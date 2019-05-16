import unittest
import log_analyzer
from datetime import datetime
from collections import OrderedDict
import os
import shelve


class LogAnalyzerTest(unittest.TestCase):
    def test_get_last_log_file(self):
        self.assertEqual(
            log_analyzer.get_last_log_file('../log'),
            log_analyzer.LogFile(
                path='../log/nginx-access-ui.log-20170630.gz',
                ext='.gz',
                date_time=datetime(2017, 6, 30, 0, 0)
            )
        )


    def test_get_log_file_tuple(self):
        self.assertEqual(
            log_analyzer.get_log_file_tuple("../log/nginx-access-ui.log-20170630.gz"),
            log_analyzer.LogFile(
                path='../log/nginx-access-ui.log-20170630.gz',
                ext='.gz',
                date_time=datetime(2017, 6, 30, 0, 0)
            )
        )

    def test_nginx_log_line_parse(self):
        log_line1 = '1.126.153.80 -  - [29/Jun/2017:04:46:00 +0300] ' \
                   '"GET /agency/outgoings_stats/?date1=28-06-2017&' \
                   'date2=28-06-2017&date_type=day&do=1&rt=banner&' \
                   'oi=25754435&as_json=1 HTTP/1.1" 200 217 "-" "-" "-" ' \
                   '"1498700760-48424485-4709-9957635" "1835ae0f17f" 0.068'
        log_line2 = '1.202.56.176 -  - [29/Jun/2017:03:59:15 +0300] "0" ' \
                    '400 166 "-" "-" "-" "-" "-" 0.000'
        self.assertEqual(
            log_analyzer.nginx_log_line_parse(log_line1),
            (
            '/agency/outgoings_stats/?date1=28-06-2017&date2=28-06-2017&'
            'date_type=day&do=1&rt=banner&oi=25754435&as_json=1',
            '0.068'
            )
        )
        self.assertEqual(
            log_analyzer.nginx_log_line_parse(log_line2),
            ('0', '0.000')
        )


    # def test_save_url_time(self):
    #     url = "/agency/outgoings_stats/?date1=28-06-2017&" \
    #           "date2=28-06-2017&date_type=day&do=1&rt=banner&" \
    #           "oi=25754435&as_json=1"
    #     time = '0.068'
    #     shelve_file = 'shelve'
    #
    #     with shelve.open(shelve_file) as db:
    #         db.clear()
    #         log_analyzer.save_url_time(url, time, db)
    #         self.assertEqual(db[url], ' 0.068')
    #         log_analyzer.save_url_time(url, '0.588', db)
    #         self.assertEqual(db[url], ' 0.068 0.588')
    def test_save_report(self):
        config = {
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "reports",
            "LOG_DIR": "log",
            "SCRIPT_LOG_FILE": "log_analyzer.log",
            "BASE_DIR": os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        }
        path_to_file = os.path.join(
                config['BASE_DIR'],
                config['REPORT_DIR']
        )
        last_log_file = log_analyzer.LogFile(
            'nginx-access-ui.log-20210630.gz',
            '.gz',
            datetime(2022, 6, 30, 0, 0)
        )
        new_report_file_name = 'report-{}.html'.format(
            last_log_file.date_time.strftime("%Y.%m.%d")
        )

        new_report_file_path = os.path.join(
            path_to_file,
            new_report_file_name,
        )
        log_analyzer.save_report('12345', last_log_file.date_time, config)
        self.assertTrue(
            os.path.isfile(new_report_file_path)
        )
        os.remove(new_report_file_path)

    def test_gen_report_list(self):
        request_dict = OrderedDict(
            [('/api/v2/banner/25019354', [0.39, 0.35]),
             ('/api/v2/banner/16852664', [0.199]),
             ('/api/1/photogenic_banners/list/?server_name=WIN7RB4', [0.133])]
        )
        report_gen = log_analyzer.gen_report_list(
            request_counter=3,
            total_request_time=1.072,
            request_order_dict=request_dict
        )
        for i, request in enumerate(report_gen, start=1):
            if i == 1:
                self.assertEqual(
                    request,
                    {'count': 2, 'time_avg': 0.37, 'time_max': 0.39,
                     'time_sum': 0.74,
                     'url': '/api/v2/banner/25019354', 'time_med': 0.37,
                     'time_perc': 69.02985074626865,
                     'count_perc': 66.66666666666667}
                )
            if i == 2:
                self.assertEqual(
                    request,
                    {'count': 1, 'time_avg': 0.199, 'time_max': 0.199,
                     'time_sum': 0.199, 'url': '/api/v2/banner/16852664',
                     'time_med': 0.199, 'time_perc': 18.563432835820898,
                     'count_perc': 33.333333333333336}
                )
            if i == 3:
                self.assertEqual(
                    request,
                    {'count': 1, 'time_avg': 0.133, 'time_max': 0.133,
                     'time_sum': 0.133,
                     'url': '/api/1/photogenic_banners/list/?server_name=WIN7RB4',
                     'time_med': 0.133, 'time_perc': 12.406716417910447,
                     'count_perc': 33.333333333333336}
                )

    def test_get_report_text(self):
        config = {
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "reports",
            "LOG_DIR": "log",
            "SCRIPT_LOG_FILE": "log_analyzer.log",
            "BASE_DIR": os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        }
        request_dict = OrderedDict(
            [('/api/v2/banner/25019354', [0.39, 0.35]),
             ('/api/v2/banner/16852664', [0.199]),
             ('/api/1/photogenic_banners/list/?server_name=WIN7RB4', [0.133])]
        )
        report_gen = log_analyzer.gen_report_list(
            request_counter=3,
            total_request_time=1.072,
            request_order_dict=request_dict
        )
        path_to_report_file = os.path.join(config['BASE_DIR'],
                                           config['REPORT_DIR'])
        with open(
                os.path.join(
                path_to_report_file, 'test_template_report_file.html'),
                  mode='tw', encoding='utf-8') as f_handler:
            f_handler.write("""
<script type="text/javascript">
    !function($) {
    var table = $$table_json;
    var reportDates;
    var columns = new Array();
    var lastRow = 150;
    var $table = $(".report-table-body");
    var $header = $(".report-table-header-row");
    var $selector = $(".report-date-selector");"""
                            )

        self.assertEqual(
            log_analyzer.get_report_text(
                report_list=list(report_gen),
                template_report_file='test_template_report_file.html',
                config=config
                ),
            """
<script type="text/javascript">
    !function($) {
    var table = [{"count": 2, "time_avg": 0.37, "time_max": 0.39, "time_sum": 0.74, "url": "/api/v2/banner/25019354", "time_med": 0.37, "time_perc": 69.02985074626865, "count_perc": 66.66666666666667}, {"count": 1, "time_avg": 0.199, "time_max": 0.199, "time_sum": 0.199, "url": "/api/v2/banner/16852664", "time_med": 0.199, "time_perc": 18.563432835820898, "count_perc": 33.333333333333336}, {"count": 1, "time_avg": 0.133, "time_max": 0.133, "time_sum": 0.133, "url": "/api/1/photogenic_banners/list/?server_name=WIN7RB4", "time_med": 0.133, "time_perc": 12.406716417910447, "count_perc": 33.333333333333336}];
    var reportDates;
    var columns = new Array();
    var lastRow = 150;
    var $table = $(".report-table-body");
    var $header = $(".report-table-header-row");
    var $selector = $(".report-date-selector");"""
        )
        os.remove(os.path.join(
                    path_to_report_file, 'test_template_report_file.html'
                ))

    # def test_get_report_text(self):
    #     pass
        # log_analyzer.get_report_text()

if __name__ == '__main__':
    unittest.main()
