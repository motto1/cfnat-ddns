import re
import requests
import json
from collections import deque
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Cloudflare API配置
API_TOKEN = "ETD34poUGnQ7Ix2InA7LCP4Ya6giLmfYsOgdWQOv"
ZONE_ID = "9c5b21516f68c785d5f013abe367598b"
DOMAIN = "cf.xn--siqq7j.us.kg"

# 日志文件路径列表 - 可以添加任意数量的日志文件路径
LOG_FILES = [
    "/mnt/sata1-1/docker/containers/53488fff0546b20153eee67b473852c23ca95eac1bdd4560e3bd047766bb21ea/53488fff0546b20153eee67b473852c23ca95eac1bdd4560e3bd047766bb21ea-json.log",
    "/mnt/sata1-1/docker/containers/13483dffe8db95d78dd6b600428fafb8e88d0ae09b0d69cc4ccd2cf50179019a/13483dffe8db95d78dd6b600428fafb8e88d0ae09b0d69cc4ccd2cf50179019a-json.log"
    # 可以继续添加更多日志文件路径
    # "/path/to/your/third/log/file.log",
    # "/path/to/your/fourth/log/file.log",
    # ...
]

def read_last_n_lines(file_path, n=100):
    """读取文件最后n行"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return list(deque(file, n))
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}")
        return []

def extract_ip_addresses(lines, file_path):
    """从单个日志文件中提取出现最多的IP地址"""
    ip_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):443'
    ip_count = {}
    
    for line in lines:
        matches = re.findall(ip_pattern, line)
        if matches:
            for ip in matches:
                ip_count[ip] = ip_count.get(ip, 0) + 1
                print(f"[{file_path}] 找到IP: {ip}, 当前出现次数: {ip_count[ip]}")
    
    if ip_count:
        most_common_ip = max(ip_count.items(), key=lambda x: x[1])
        print(f"\n[{file_path}] 出现最多的IP是: {most_common_ip[0]}, 出现次数: {most_common_ip[1]}")
        return most_common_ip[0]
    return None

# 创建一个带有重试机制的session
def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=5,  # 最多重试5次
        backoff_factor=1,  # 重试间隔
        status_forcelist=[408, 429, 500, 502, 503, 504],  # 需要重试的HTTP状态码
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def delete_all_dns_records(headers):
    """删除所有匹配域名的DNS记录"""
    url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records"
    session = create_session()
    
    try:
        # 获取所有DNS记录
        response = session.get(url, headers=headers)
        response.raise_for_status()
        records = response.json()['result']
        
        # 找到所有匹配域名的记录
        domain_records = [record for record in records if record['name'] == DOMAIN]
        
        if not domain_records:
            print(f"没有找到域名 {DOMAIN} 的DNS记录")
            return True
            
        print(f"找到 {len(domain_records)} 条DNS记录需要删除")
        
        # 删除所有匹配的记录
        for record in domain_records:
            delete_url = f"{url}/{record['id']}"
            try:
                delete_response = session.delete(delete_url, headers=headers)
                delete_response.raise_for_status()
                print(f"成功删除DNS记录: {record['content']}")
                time.sleep(1)  # 每次删除后等待1秒
            except Exception as e:
                print(f"删除记录 {record['content']} 时出错: {e}")
                continue
        
        print("所有旧记录已删除，等待DNS同步...")
        time.sleep(5)  # 等待5秒确保所有删除操作完成同步
        
        # 验证是否所有记录都已删除
        verify_response = session.get(url, headers=headers)
        verify_response.raise_for_status()
        remaining_records = [r for r in verify_response.json()['result'] if r['name'] == DOMAIN]
        
        if remaining_records:
            print("警告：仍有DNS记录未删除完全")
            return False
            
        print("验证完成：所有旧记录已成功删除")
        return True
        
    except requests.exceptions.SSLError as e:
        print(f"SSL错误: {e}")
        print("尝试使用不同的SSL配置重试...")
        try:
            # 禁用SSL验证重试
            response = requests.get(url, headers=headers, verify=False)
            print("使用禁用SSL验证的方式成功连接")
            return delete_all_dns_records(headers)  # 递归重试
        except Exception as e2:
            print(f"重试失败: {e2}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"删除DNS记录时出错: {e}")
        return False
    finally:
        session.close()

def create_dns_record(ip, headers):
    """创建新的DNS记录，关闭CDN代理"""
    url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records"
    session = create_session()
    
    try:
        data = {
            "type": "A",
            "name": DOMAIN,
            "content": ip,
            "proxied": False,  # 关闭CDN代理
            "ttl": 120  # 设置TTL为120秒
        }
        response = session.post(url, headers=headers, json=data)
        
        response_json = response.json()
        if not response.ok:
            error_messages = response_json.get('errors', [])
            for error in error_messages:
                print(f"API错误: {error.get('message', '未知错误')}")
                print(f"错误代码: {error.get('code', '未知代码')}")
            print(f"完整响应: {response_json}")
            return False
            
        print(f"已创建新的DNS记录，IP: {ip}，CDN已关闭")
        return True
        
    except requests.exceptions.SSLError as e:
        print(f"SSL错误: {e}")
        try:
            # 禁用SSL验证重试
            response = requests.post(url, headers=headers, json=data, verify=False)
            print("使用禁用SSL验证的方式成功创建记录")
            return True
        except Exception as e2:
            print(f"重试失败: {e2}")
            return False
    except Exception as e:
        print(f"创建DNS记录时出错: {e}")
        return False
    finally:
        session.close()

def update_cloudflare_dns(ip_list):
    """更新Cloudflare DNS记录"""
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 验证API Token是否有效
    try:
        verify_url = "https://api.cloudflare.com/client/v4/user/tokens/verify"
        response = requests.get(verify_url, headers=headers)
        response_json = response.json()
        if not response_json.get('success', False):
            print("API Token验证失败:")
            print(response_json)
            return
        print("API Token验证成功")
    except Exception as e:
        print(f"验证API Token时出错: {e}")
        return
    
    # 首先确保删除所有现有记录
    print("\n开始删除所有现有DNS记录...")
    if not delete_all_dns_records(headers):
        print("删除现有记录失败，终止操作")
        return
    
    # 为每个IP创建新记录
    print("\n开始创建新的DNS记录...")
    for ip in ip_list:
        if ip:  # 只处理有效的IP
            if not create_dns_record(ip, headers):
                print(f"为IP {ip} 创建DNS记录失败，尝试下一个IP")
            else:
                time.sleep(2)  # 在创建记录之间添加短暂延迟

def process_log_files(log_files):
    """处理所有日志文件并返回IP列表"""
    ip_list = []
    total_files = len(log_files)
    
    print(f"\n开始处理 {total_files} 个日志文件...")
    
    for index, log_file in enumerate(log_files, 1):
        print(f"\n处理第 {index}/{total_files} 个日志文件: {log_file}")
        lines = read_last_n_lines(log_file)
        if lines:
            most_common_ip = extract_ip_addresses(lines, log_file)
            if most_common_ip:
                ip_list.append(most_common_ip)
        else:
            print(f"警告: 无法读取日志文件 {log_file} 或文件为空")
    
    return ip_list

def main():
    # 处理所有日志文件
    ip_list = process_log_files(LOG_FILES)
    
    if not ip_list:
        print("错误: 未从任何日志文件中找到有效IP")
        return
    
    # 显示找到的所有IP
    print("\n找到的所有IP:")
    for index, ip in enumerate(ip_list, 1):
        print(f"{index}. {ip}")
    
    # 更新DNS记录
    print(f"\n将更新以下IP到DNS记录: {ip_list}")
    update_cloudflare_dns(ip_list)

if __name__ == "__main__":
    main()
