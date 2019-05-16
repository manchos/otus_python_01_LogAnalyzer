#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from collections import namedtuple, defaultdict, OrderedDict, Counter
import re
from datetime import datetime
import gzip
from itertools import islice
import logging
from tqdm import tqdm
from statistics import median
from string import Template
import json

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "reports",
    "LOG_DIR": "log",
    "SCRIPT_LOG_FILE": "log_analyzer.log",
    "BASE_DIR": os.path.dirname(os.path.abspath(__file__))

}

logging.basicConfig(format='[%(asctime)s]%(msecs)d %(levelname)s %(message)s',
                    datefmt='%Y.%m.%d %H:%M:%S',
                    level=logging.DEBUG,
                    filename=config['SCRIPT_LOG_FILE'])

LogFile = namedtuple('LogFile', ['path', 'ext', 'date_time'])

os.path.splitext("nginx-access-ui.log-20170630.gz")

def read_file(path, block_size=1048576):
    with gzip.open(path, 'rt') as f:
        while True:
            piece = f.read(block_size)
            if piece:
                yield piece
            else:
                return


def line_from_gzip_file(file_path, max_line=None):
    with gzip.open(file_path, 'rt', encoding='utf8') as f:
        # file_content = f.read()
        for i, line in enumerate(f, start=1):
            if max_line is not None:
                if i > max_line:
                    break
            yield nginx_log_line_parse(line)


# '1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752759" "dc7161be3" 0.390'
# '1.99.174.176 3b81f63526fa8  - [29/Jun/2017:03:50:22 +0300] "GET /api/1/photogenic_banners/list/?server_name=WIN7RB4 HTTP/1.1" 200 12 "-" "Python-urllib/2.7" "-" "1498697422-32900793-4708-9752770" "-" 0.133'

def nginx_log_line_parse(
        log_line,
        log_template='$remote_addr $remote_user  $http_x_real_ip [$time_local] '
               '"$request" $status $body_bytes_sent "$http_referer" '
               '"$http_user_agent" "$http_x_forwarded_for" '
               '"$http_X_REQUEST_ID" "$http_X_RB_USER" $request_time',
):
    str_shield = re.sub(r'([\[\]\"\{\}]{1})', r'\\\1', log_template)
    vars_patt = re.sub('\$(\w+)', r'(?P<\1>.+)', str_shield)

    vars_matches = re.search(vars_patt, log_line)

    request_time = vars_matches['request_time']
    request = vars_matches['request']
    request_patt = re.compile('((GET|POST) (?P<url>.+) (http\/\d\.\d))', re.I)

    request_match = re.search(request_patt, request)
    url = request_match['url'] if request_match else request

    return url, request_time



def get_log_file_tuple(file_path, exts=('.gz', '.txt'), date_pat="%Y%m%d"):
    """
    :param file_path str
    Возвращает namedtuple LogFile с указанием пути до него,
    распаршенной через datetime даты из имени файла и расширением,
    с указанием пути до него, распаршенной через datetime даты из
    имени файла и расширением,

    :return: namedtuple('LogFile', ['path', 'ext', 'date_time']),
    None if not match "%Y%m%d"
    """
    date_pat_match_dict = dict(
        zip("%Y %m %d".split(), '\d{4} \d{2} \d{2}'.split())
    )
    re_from_date_pat = date_pat
    for key, val in date_pat_match_dict.items():
        re_from_date_pat = re_from_date_pat.replace(key, val)

    path, filename = os.path.split(file_path)
    basename, ext = os.path.splitext(filename)
    date_match = re.search(re_from_date_pat, basename, re.M | re.I)

    if not date_match and ext not in exts or ext.startswith('.log'):
        return None

    return LogFile(
        path=file_path,
        ext=ext,
        date_time=datetime.strptime(date_match.group(), date_pat)
    )


def get_last_log_file(log_dir):
    """
    найти самый свежий лог
    можно за один проход по файлам, без использования glob, сортировки и т.п.
    из функции, которая будет искать последний лог удобно возвращать  например.
    распаршенная дата из имени логфайла пригодится, чтобы составить путь
    до отчета, это можно сделать "за один присест",
    не нужно проходится по всем файлам и что‑то искать.
    :return: namedtuple('LogFile', ['path', 'ext', 'date_time'])
    """
    print(os.path.isdir(log_dir))
    if not os.path.isdir(log_dir):
        raise ValueError(
            "{} must be a real directory".format(log_dir)
        )
    last_log_file = LogFile('', '', date_time=datetime(1970, 1, 1))

    for address, dirs, files in os.walk(log_dir):
        for file in files:
            log_file = get_log_file_tuple(os.path.join(address, file))
            if log_file is None:
                continue

            if log_file.date_time > last_log_file.date_time:
                last_log_file = log_file

    return last_log_file

def main():
    pass

def save_url_time(url, time, shelve_db):
    entry = shelve_db.get(url, '')
    shelve_db[url] = '{} {}'.format(entry, time)


def get_url_and_time_dict_from_nginx_log_file(file, config):
    url_dict = defaultdict(list)
    total_request_time = 0.0
    request_counter = 1
    for url_str, request_time_str in tqdm(line_from_gzip_file(file, max_line=5)):
        # print(url_str, request_time_str)
        try:
            request_time = float(request_time_str)
        except ValueError:
            logging.exception("request_time must be a float")

        total_request_time += request_time
        request_counter += 1

        url_dict[url_str].append(request_time)

    requests_order_dict = OrderedDict(
        islice(
            sorted(url_dict.items(), key=lambda x: max(x[1]), reverse=True),
            config["REPORT_SIZE"]
        )
    )
    return request_counter, total_request_time, requests_order_dict


def gen_report_list(request_counter, total_request_time, request_order_dict):
    """
    :param request_counter: total number of requests int
    :param total_request_time: total_request_time
    :param request_order_dict:
    :return: dict
    'count',  # сколько раз встречается URL, абсолютное значение
    'time_avg',  # средний $request_time для данного URL'а
    'time_max',  # максимальный $request_time для данного URL'а
    'time_sum',  # суммарный $request_time для данного URL'а, абсолютное значение
    'url',
    'time_med',  # медиана $request_time для данного URL'а
    'time_perc',  # суммарный $request_time для данного URL'а, в процентах
                  # относительно общего $request_time всех запросов
    'count_perc',  # сколько раз встречается URL, в процентнах относительно
                    #относительно общего $request_time всех запросов
    """

    for request_url, request_time_list in request_order_dict.items():
        request_time_sum = sum(request_time_list)
        yield {
            'count': len(request_time_list),
            'time_avg': request_time_sum /len(request_time_list),
            'time_max': max(request_time_list),
            'time_sum': request_time_sum,
            'url': request_url,
            'time_med': median(request_time_list),
            'time_perc': 100*request_time_sum/total_request_time,
            'count_perc': 100 * len(request_time_list) / request_counter
        }


def get_report_text(report_list, template_report_file, config,
                    report_list_var='table_json'):
    path_to_template_report_file = os.path.join(
        config['BASE_DIR'], config['REPORT_DIR'], template_report_file
    )

    class MyTemplate(Template):
        delimiter = '$$'
        idpattern = '[a-z]+_[a-z]+'

    with open(path_to_template_report_file, 'rt', encoding='utf8') as f:
        report_text = MyTemplate(f.read())
        report_json_key_val = {
            report_list_var: json.dumps(report_list, ensure_ascii=False)
        }
        new_report_text = report_text.substitute(report_json_key_val)
        return new_report_text


def save_report(report_text, date_time, config):
    report_dir = os.path.join(config['BASE_DIR'], config['REPORT_DIR'])
    new_report_file_name = 'report-{}.html'.format(
        date_time.strftime("%Y.%m.%d")
    )
    with open(os.path.join(report_dir, new_report_file_name),
              mode='tw', encoding='utf-8') as f_handler:
        f_handler.write(report_text)



if __name__ == "__main__":

    last_log_file = get_last_log_file('./log')
    print("\n\n{}".format(last_log_file))


    request_counter, total_request_time, url_order_dict = \
        get_url_and_time_dict_from_nginx_log_file(
        "./log/nginx-access-ui.log-20170630.gz", config)
    print(request_counter, total_request_time, url_order_dict)

    # for request_counter in gen_report_list(request_counter, total_request_time, url_order_dict):
    #     print(request_counter)

    report_text = get_report_text(
        list(gen_report_list(request_counter, total_request_time, url_order_dict)),
        template_report_file=os.path.join(
            config['BASE_DIR'],
            config['REPORT_DIR'],
            'report.html'
        )
    )

    save_report(
        report_text=report_text,
        date_time=last_log_file.date_time,
        config={
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "reports",
            "LOG_DIR": "log",
            "SCRIPT_LOG_FILE": "log_analyzer.log",
            "BASE_DIR": os.path.dirname(os.path.abspath(__file__))
        }
    )


    main()
