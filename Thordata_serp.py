#!/usr/bin/env python3
"""
SerpAPI Performance Test Script
Tests SerpAPI service with configurable engines, concurrency, and detailed performance metrics.
"""

import http.client
import csv
import time
import json
import argparse
import concurrent.futures
from urllib.parse import urlencode, urlparse
from datetime import datetime
from collections import defaultdict
import ssl
import math


class SerpAPITester:
    """SerpAPI性能测试类"""

    # SerpAPI支持的所有引擎
    SUPPORTED_ENGINES = [
        'google', 'google_local', 'google_images',
        'google_videos', 'google_news', 'google_shopping'
    ]

    def __init__(self, api_key, save_details=False):
        """
        初始化SerpAPI测试器

        Args:
            api_key: SerpAPI认证密钥
            save_details: 是否保存每个请求的详细CSV记录
        """
        self.api_key = api_key
        self.host = "scraperapi.thordata.com"
        self.save_details = save_details
        self.keyword_pool = [
            "pizza", "coffee", "restaurant", "weather", "news",
            "hotel", "flight", "car", "phone", "laptop",
            "book", "music", "movie", "game", "sport",
            "health", "fitness", "recipe", "travel", "shopping",
            "weather tomorrow", "nearby restaurants", "best cafes",
            "smartwatch", "headphones", "tablet", "camera",
            "electric car", "used cars", "car rental",
            "cheap flights", "flight status", "airport",
            "luxury hotel", "hostel", "airbnb",
            "stock market", "bitcoin", "currency exchange",
            "technology", "ai news", "space exploration",
            "basketball", "football", "tennis",
            "concert", "festival", "museum",
            "shopping mall", "discounts", "coupons",
            "recipes easy", "vegan recipes", "healthy meals",
            "pharmacy", "clinic near me", "dentist",
            "fitness gym", "workout plan", "yoga",
            "mobile games", "pc games", "game reviews",
            "movies 2025", "tv shows", "cartoon",
            "books best seller", "novels", "ebooks"
        ]

    def make_request(self, engine, query):
        """
        发送单个API请求并测量准确的响应时间

        Args:
            engine: 搜索引擎名称
            query: 搜索关键词

        Returns:
            dict: 包含请求结果的字典
        """
        result = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'product': 'SerpAPI',
            'engine': engine,
            'query': query,
            'status_code': None,
            'response_time': None,
            'response_size': None,
            'success': False,
            'error': '',
            'response_excerpt': ''
        }

        conn = None
        #Thordata的请求方式
        try:
            params = {
                "engine": engine,
                "q": query,
                "json": "1",
                "no_cache": "true"
            }
            payload = urlencode(params)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            path = "/request"
            conn = http.client.HTTPSConnection(self.host, timeout=30)

            start_time = time.time()
            conn.request("POST", path, payload, headers)

            response = conn.getresponse()
            data = response.read()
            end_time = time.time()

            result['response_time'] = round(end_time - start_time, 3)
            result['status_code'] = response.status
            result['response_size'] = round(len(data) / 1024, 3)

            # ---- ★ 修复：Thordata 响应是 JSON 字符串，需要 double JSON decode ★ ----
            text = data.decode("utf-8", errors="ignore")
            result['response_excerpt'] = text[:1000]

            try:
                # 第一次解析：从原始文本 -> JSON 字符串
                first_parsed = json.loads(text)

                # 如果结果仍是字符串，说明还需要第二次解析
                if isinstance(first_parsed, str):
                    response_json = json.loads(first_parsed)
                else:
                    response_json = first_parsed

            except Exception as e:
                result['success'] = False
                result['error'] = f"Non-JSON response: {str(e)}"
                return result

            # ---- ★ JSON 一定是 dict，到这里保持 dict，不再覆盖 ★ ----
            result['success'] = self._is_response_successful(response_json, response.status)

            if not result['success']:
                result['error'] = self._extract_error_message(response_json)

            return result

        except Exception as e:
            result['success'] = False
            result['error'] = f"Request error: {str(e)}"
            if 'start_time' in locals():
                result['response_time'] = round(time.time() - start_time, 3)
            return result

        finally:
            if conn:
                conn.close()

        return result

    def _is_response_successful(self, response_json, status_code):

        # HTTP 必须是 200
        if status_code != 200:
            return False

        # Thordata 成功标记
        if response_json.get("search_metadata", {}).get("status") == "Success":
            return True

        # SerpAPI 风格字段兼容
        result_fields = [
            "organic_results",
            "shopping_results",
            "news_results",
            "images_results",
            "videos_results",
            "local_results",
            "ai_overview",
            "search_information",
        ]
        return any(field in response_json for field in result_fields)

    def _extract_error_message(self, response_json):

        if isinstance(response_json, dict):

            # Thordata 的错误字段（只有失败情况才会出现）
            if "error" in response_json:
                return response_json["error"]

            # 非成功：检查 search_metadata 状态
            status = response_json.get("search_metadata", {}).get("status")
            if status and status != "Success":
                return f"Status: {status}"

            return "No error field found"

        # 理论上不会发生，但放在这里兜底
        return "Invalid JSON structure"

    def _extract_response_summary(self, response_json):
        """
        提取响应摘要信息

        Args:
            response_json: 解析后的JSON响应

        Returns:
            str: 响应摘要
        """
        summary_parts = []

        # 提取搜索信息
        if 'search_information' in response_json:
            info = response_json['search_information']
            if 'total_results' in info:
                summary_parts.append(f"total_results:{info['total_results']}")

        # 统计各类结果数量
        if 'organic_results' in response_json:
            summary_parts.append(f"organic:{len(response_json['organic_results'])}")
        if 'shopping_results' in response_json:
            summary_parts.append(f"shopping:{len(response_json['shopping_results'])}")
        if 'images_results' in response_json:
            summary_parts.append(f"images:{len(response_json['images_results'])}")

        return ", ".join(summary_parts) if summary_parts else "Success"

    def run_concurrent_test(self, engine, num_requests, concurrency, query=None):
        """
        运行并发性能测试

        Args:
            engine: 搜索引擎名称
            num_requests: 总请求数
            concurrency: 并发数
            query: 搜索关键词（可选，默认随机）

        Returns:
            list: 所有请求结果
        """
        results = []

        # 如果未指定query，使用随机关键词
        queries = []
        if query:
            queries = [query] * num_requests
        else:
            # 循环使用关键词池
            queries = [self.keyword_pool[i % len(self.keyword_pool)] for i in range(num_requests)]

        print(f"\n开始测试引擎: {engine}")
        print(f"  总请求数: {num_requests}")
        print(f"  并发数: {concurrency}")
        print(f"  缓存: 禁用 (no_cache=true)")
        print("-" * 80)

        # 记录并发测试的总开始时间
        total_start_time = time.time()

        # 使用线程池进行并发测试
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            # 提交所有任务
            future_to_index = {
                executor.submit(self.make_request, engine, queries[i]): i
                for i in range(num_requests)
            }

            # 收集结果
            completed = 0
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1

                    # 显示进度
                    if completed % max(1, num_requests // 10) == 0 or completed == num_requests:
                        print(f"  进度: {completed}/{num_requests} 完成")

                except Exception as e:
                    print(f"  请求 {index + 1} 异常: {str(e)}")

        # 记录并发测试的总结束时间
        total_end_time = time.time()
        total_duration = round(total_end_time - total_start_time, 3)

        print(f"\n并发测试完成，总耗时: {total_duration}秒")

        return results, total_duration

    def run_all_engines_test(self, engines, num_requests_per_engine, concurrency):
        """
        测试多个引擎的性能

        Args:
            engines: 要测试的引擎列表
            num_requests_per_engine: 每个引擎的请求数
            concurrency: 并发数

        Returns:
            dict: 所有引擎的测试结果
        """
        all_results = {}
        all_statistics = []

        print("=" * 80)
        print("开始批量引擎性能测试")
        print("=" * 80)

        for engine in engines:
            try:
                results, total_duration = self.run_concurrent_test(
                    engine, num_requests_per_engine, concurrency
                )

                all_results[engine] = results

                # 计算统计数据
                stats = self._calculate_statistics(
                    'SerpAPI', engine, results, num_requests_per_engine,
                    concurrency, total_duration
                )
                all_statistics.append(stats)

                # 如果启用详细记录，保存CSV
                if self.save_details:
                    self._save_detailed_csv(engine, results)

            except Exception as e:
                print(f"\n引擎 {engine} 测试失败: {str(e)}")
                continue

        return all_results, all_statistics

    def _calculate_statistics(self, product, engine, results, total_requests,
                              concurrency, total_duration):
        """
        计算统计数据

        Returns:
            dict: 统计数据
        """
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]

        success_count = len(successful_results)
        success_rate = round(success_count / total_requests * 100, 2) if total_requests > 0 else 0

        # 计算成功请求的平均响应时间
        avg_response_time = 0
        if successful_results:
            total_time = sum(r['response_time'] for r in successful_results if r['response_time'])
            avg_response_time = round(total_time / len(successful_results), 3)

        # 计算P90延迟 (90th percentile)
        p90_latency = 0
        if successful_results:
            response_times = sorted([r['response_time'] for r in successful_results if r['response_time']])
            if response_times:
                # 使用ceil(0.9 × N)计算P90索引
                p90_index = math.ceil(len(response_times) * 0.9) - 1  # -1因为索引从0开始
                if p90_index < 0:
                    p90_index = 0
                if p90_index >= len(response_times):
                    p90_index = len(response_times) - 1
                p90_latency = round(response_times[p90_index], 3)

        # 计算请求速率 (秒/请求)
        request_rate = round(total_duration / total_requests, 3) if total_requests > 0 else 0

        # 计算成功请求的平均响应大小
        avg_response_size = 0
        if successful_results:
            total_size = sum(r['response_size'] for r in successful_results if r['response_size'])
            avg_response_size = round(total_size / len(successful_results), 3)

        stats = {
            '产品类别': product,
            '引擎': engine,
            '请求总数': total_requests,
            '并发数': concurrency,
            '请求速率(s/req)': request_rate,
            '成功次数': success_count,
            '成功率(%)': success_rate,
            '成功平均响应时间(s)': avg_response_time,
            'P90延迟(s)': p90_latency,
            '并发完成时间(s)': total_duration,
            '成功平均响应大小(KB)': avg_response_size
        }

        return stats

    def _save_detailed_csv(self, engine, results):
        """
        保存详细的请求记录到CSV

        Args:
            engine: 引擎名称
            results: 请求结果列表
        """
        filename = f"serpapi_{engine}_detailed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        fieldnames = [
            'timestamp', 'product', 'engine', 'query', 'status_code',
            'response_time', 'response_size', 'success', 'error', 'response_excerpt'
        ]

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        print(f"  详细记录已保存到: {filename}")

    def save_summary_statistics(self, statistics, filename='serpapi_summary_statistics.csv'):
        """
        保存汇总统计表

        Args:
            statistics: 统计数据列表
            filename: 输出文件名
        """
        if not statistics:
            print("没有统计数据可保存")
            return

        fieldnames = [
            '产品类别', '引擎', '请求总数', '并发数', '请求速率(s/req)',
            '成功次数', '成功率(%)', '成功平均响应时间(s)', 'P90延迟(s)',
            '并发完成时间(s)', '成功平均响应大小(KB)'
        ]

        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(statistics)

        print(f"\n{'=' * 80}")
        print(f"汇总统计表已保存到: {filename}")
        print(f"{'=' * 80}")

        # 打印统计表
        self._print_statistics_table(statistics)

    def _print_statistics_table(self, statistics):
        """
        在控制台打印统计表

        Args:
            statistics: 统计数据列表
        """
        print("\n汇总统计表:")
        print("-" * 160)

        # 打印表头
        header = f"{'引擎':<20} {'请求数':>8} {'并发':>6} {'速率(s/req)':>12} " \
                 f"{'成功':>8} {'成功率':>8} {'平均响应(s)':>12} {'P90延迟(s)':>11} {'完成时间(s)':>12} {'响应大小(KB)':>14}"
        print(header)
        print("-" * 160)

        # 打印数据行
        for stat in statistics:
            row = f"{stat['引擎']:<20} {stat['请求总数']:>8} {stat['并发数']:>6} " \
                  f"{stat['请求速率(s/req)']:>12} {stat['成功次数']:>8} " \
                  f"{stat['成功率(%)']:>7}% {stat['成功平均响应时间(s)']:>12} " \
                  f"{stat['P90延迟(s)']:>11} {stat['并发完成时间(s)']:>12} {stat['成功平均响应大小(KB)']:>14}"
            print(row)

        print("-" * 160)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='SerpAPI性能测试脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 测试单个引擎
  python serpapi_test.py -k YOUR_API_KEY -e google -n 10 -c 5

  # 测试多个引擎
  python serpapi_test.py -k YOUR_API_KEY -e google bing yahoo -n 20 -c 10

  # 测试所有引擎
  python serpapi_test.py -k YOUR_API_KEY --all-engines -n 10 -c 5

  # 启用详细CSV记录
  python serpapi_test.py -k YOUR_API_KEY -e google -n 10 -c 5 --save-details
        """
    )

    parser.add_argument('-k', '--api-key', type=str,
                        help='SerpAPI认证密钥')
    parser.add_argument('-e', '--engines', type=str, nargs='+',
                        help='要测试的搜索引擎列表')
    parser.add_argument('--all-engines', action='store_true',
                        help='测试所有支持的引擎')
    parser.add_argument('-n', '--num-requests', type=int, default=10,
                        help='每个引擎的请求数 (默认: 10)')
    parser.add_argument('-c', '--concurrency', type=int, default=5,
                        help='并发数 (默认: 5)')
    parser.add_argument('-q', '--query', type=str,
                        help='搜索关键词 (默认: 随机)')
    parser.add_argument('--save-details', action='store_true',
                        help='保存每个请求的详细CSV记录')
    parser.add_argument('-o', '--output', type=str,
                        default='serpapi_summary_statistics.csv',
                        help='汇总统计表输出文件名')
    parser.add_argument('--list-engines', action='store_true',
                        help='列出所有支持的引擎')

    args = parser.parse_args()

    # 列出所有支持的引擎
    if args.list_engines:
        print("支持的搜索引擎:")
        for i, engine in enumerate(SerpAPITester.SUPPORTED_ENGINES, 1):
            print(f"  {i:2d}. {engine}")
        return

    # 验证API密钥
    if not args.api_key:
        print("错误: 请使用 -k 或 --api-key 指定API密钥")
        return

    # 确定要测试的引擎
    if args.all_engines:
        engines = SerpAPITester.SUPPORTED_ENGINES
        print(f"将测试所有 {len(engines)} 个引擎")
    elif args.engines:
        engines = args.engines
        # 验证引擎是否支持
        invalid_engines = [e for e in engines if e not in SerpAPITester.SUPPORTED_ENGINES]
        if invalid_engines:
            print(f"警告: 以下引擎不在支持列表中: {', '.join(invalid_engines)}")
            print("使用 --list-engines 查看支持的引擎列表")
    else:
        print("错误: 请使用 -e 指定引擎或使用 --all-engines 测试所有引擎")
        print("使用 --list-engines 查看支持的引擎列表")
        return

    # 创建测试器
    tester = SerpAPITester(args.api_key, save_details=args.save_details)

    # 运行测试
    all_results, all_statistics = tester.run_all_engines_test(
        engines, args.num_requests, args.concurrency
    )

    # 保存汇总统计
    tester.save_summary_statistics(all_statistics, args.output)

    print("\n测试完成!")


if __name__ == "__main__":
    main()
