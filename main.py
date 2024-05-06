import json
from datetime import datetime
from haralyzer import HarParser
import pytz
from datetime import timedelta
from urllib.parse import urlparse, urlunparse


def parse_har_file(file_path):
    """从HAR文件中解析HTTP请求"""
    with open(file_path, 'r', encoding='utf-8-sig') as file:
        har_data = json.load(file)
    parser = HarParser(har_data)
    return parser.har_data['entries']


def to_domain_clean(url: str):
    return urlparse(url).hostname.replace('.', '_')


def to_elapsed_formatted(elapsed_ms):
    elapsed_formatted = str(timedelta(milliseconds=elapsed_ms))
    # 确保毫秒部分总是显示，即使时间差很短
    elapsed_parts = elapsed_formatted.split('.')
    if len(elapsed_parts) == 1:  # 没有毫秒部分
        elapsed_formatted += ".000"
    elif len(elapsed_parts[1]) < 3:  # 毫秒部分不足3位，补零
        elapsed_formatted = elapsed_parts[0] + "." + elapsed_parts[1].ljust(3, '0')
    elif len(elapsed_parts[1]) > 3:
        elapsed_formatted = elapsed_parts[0] + "." + elapsed_parts[1][:3]
    return elapsed_formatted


def to_plantuml_sequence_with_relative_timestamps(entries):
    """生成带时间戳的PlantUML序列图文本，保持请求的原始顺序"""
    plantuml_text = "@startuml uml\n"
    plantuml_text += 'autonumber "<b>[000]"\n'
    plantuml_participant = "actor User\nparticipant Client as Client\n"
    plantuml_body = ""
    base_time = datetime.fromisoformat(entries[0]['startedDateTime']).replace(tzinfo=pytz.UTC)
    # 记录第一个请求的绝对时间戳，用于计算偏移量

    plantuml_body = []

    for entry in entries:
        domain = urlparse(entry['request']['url']).hostname
        domain_clean = to_domain_clean(entry['request']['url'])
        # 如果域尚未作为参与者添加，则添加之
        if domain_clean not in plantuml_participant:
            plantuml_participant += f"participant {domain} as {domain_clean} \n"

        # 计算当前请求相对于第一个请求的偏移时间（毫秒）
        elapsed_ms = (datetime.fromisoformat(entry['startedDateTime']).replace(tzinfo=pytz.UTC) - base_time).total_seconds() * 1000

        # 将毫秒转换为易于阅读的格式，包括小时、分钟、秒和毫秒
        elapsed_formatted = to_elapsed_formatted(elapsed_ms)
        elapsed_formatted_end = to_elapsed_formatted(elapsed_ms + entry['time'])

        # 由于直接使用timedelta可能不包含毫秒部分，我们手动格式化确保毫秒的显示
        # 添加相对时间戳和请求-响应交互
        plantuml_req = f"note right of Client : start {elapsed_formatted}\n"
        plantuml_req += f"Client -> {to_domain_clean(entry['request']['url'])} ++: (Complete in {entry['time'] / 1000:.3f}s) {entry['request']['method']} {entry['request']['url']}\n"
        plantuml_body.append((elapsed_ms, plantuml_req))
        # 假设无需为响应添加额外的时间标签，因为响应通常紧接着请求
        plantuml_res = f"{to_domain_clean(entry['request']['url'])} --> Client --: ({entry['response']['status']}) Response {entry['request']['method']} {entry['request']['url']}\n"
        plantuml_res += f"note right of Client : ended {elapsed_formatted_end}\n"
        plantuml_body.append((elapsed_ms + entry['time'], plantuml_res))

    plantuml_body = sorted(plantuml_body, key=lambda x: x[0])
    plantuml_text += plantuml_participant
    plantuml_text += ''.join(str(ele) for ele in [body[1] for body in plantuml_body])
    plantuml_text += "@enduml"
    return plantuml_text


if __name__ == "__main__":
    har_file_path = 'har/web.har'  # 替换为你的HAR文件路径
    timestamps_info = parse_har_file(har_file_path)
    print(to_plantuml_sequence_with_relative_timestamps(timestamps_info))
