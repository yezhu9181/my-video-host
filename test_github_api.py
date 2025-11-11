#!/usr/bin/env python3
"""
测试 GitHub API 是否能获取最新数据
"""

import json
import requests
import time
from pathlib import Path

def test_github_api():
    """测试 GitHub API"""
    local_file = Path("videos.json")
    api_url = "https://api.github.com/repos/yezhu9181/my-video-host/contents/videos.json?ref=main"
    
    print("=" * 60)
    print("测试 GitHub API 获取数据")
    print("=" * 60)
    
    # 读取本地文件
    print("\n1. 读取本地 videos.json 文件...")
    if not local_file.exists():
        print("❌ 本地文件不存在")
        return False
    
    with open(local_file, 'r', encoding='utf-8') as f:
        local_data = json.load(f)
    
    local_last_updated = local_data.get('lastUpdated', 'N/A')
    local_cache_version = local_data.get('cacheVersion', 'N/A')
    
    print(f"   ✅ 本地文件读取成功")
    print(f"   - 更新时间: {local_last_updated}")
    print(f"   - 缓存版本: {local_cache_version}")
    
    # 方法1: 使用 GitHub API Raw 端点
    print(f"\n2. 测试 GitHub API Raw 端点...")
    try:
        response = requests.get(api_url, 
                              headers={'Accept': 'application/vnd.github.v3.raw'},
                              timeout=10)
        
        if response.status_code == 200:
            # Raw 端点直接返回文件内容（文本）
            api_data = json.loads(response.text)
            api_last_updated = api_data.get('lastUpdated', 'N/A')
            api_cache_version = api_data.get('cacheVersion', 'N/A')
            
            print(f"   ✅ GitHub API Raw 端点成功")
            print(f"   - 更新时间: {api_last_updated}")
            print(f"   - 缓存版本: {api_cache_version}")
            
            if (api_last_updated == local_last_updated and 
                api_cache_version == local_cache_version):
                print(f"\n   ✅ 数据一致！GitHub API 返回的是最新数据")
                return True
            else:
                print(f"\n   ⚠️  数据不一致")
        else:
            print(f"   ❌ HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    # 方法2: 使用标准 GitHub API
    print(f"\n3. 测试 GitHub API 标准端点...")
    try:
        response = requests.get(api_url, 
                              headers={'Accept': 'application/vnd.github.v3+json'},
                              timeout=10)
        
        if response.status_code == 200:
            api_response = response.json()
            if api_response.get('content'):
                import base64
                decoded_content = base64.b64decode(api_response['content'].replace('\n', ''))
                api_data = json.loads(decoded_content.decode('utf-8'))
                
                api_last_updated = api_data.get('lastUpdated', 'N/A')
                api_cache_version = api_data.get('cacheVersion', 'N/A')
                
                print(f"   ✅ GitHub API 标准端点成功")
                print(f"   - 更新时间: {api_last_updated}")
                print(f"   - 缓存版本: {api_cache_version}")
                
                if (api_last_updated == local_last_updated and 
                    api_cache_version == local_cache_version):
                    print(f"\n   ✅ 数据一致！GitHub API 返回的是最新数据")
                    return True
                else:
                    print(f"\n   ⚠️  数据不一致")
        else:
            print(f"   ❌ HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    return False

if __name__ == "__main__":
    success = test_github_api()
    exit(0 if success else 1)

