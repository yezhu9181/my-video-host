#!/usr/bin/env python3
"""
测试前端行为：模拟前端代码的执行流程
"""

import json
import requests
import time
from pathlib import Path

def test_frontend_behavior():
    """模拟前端代码的执行流程"""
    print("=" * 60)
    print("测试前端行为：模拟前端代码执行流程")
    print("=" * 60)
    
    # 读取本地文件
    local_file = Path("videos.json")
    with open(local_file, 'r', encoding='utf-8') as f:
        local_data = json.load(f)
    
    local_last_updated = local_data.get('lastUpdated')
    local_cache_version = local_data.get('cacheVersion')
    expected_commit_sha = local_data.get('latestCommitSha')
    
    print(f"\n1. 本地数据:")
    print(f"   - 更新时间: {local_last_updated}")
    print(f"   - 缓存版本: {local_cache_version}")
    print(f"   - Commit SHA: {expected_commit_sha}")
    
    # 步骤1: 从 GitHub Raw URL 获取数据（模拟前端步骤1）
    print(f"\n2. 步骤1: 从 GitHub Raw URL 获取数据和 commit SHA...")
    try:
        timestamp = int(time.time())
        random_str = str(time.time()).replace('.', '')
        raw_url = f"https://raw.githubusercontent.com/yezhu9181/my-video-host/main/videos.json?t={timestamp}&r={random_str}&_cb={timestamp}_{random_str}&nocache=1"
        
        response = requests.get(raw_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            commit_sha = data.get('latestCommitSha')
            last_updated = data.get('lastUpdated')
            cache_version = data.get('cacheVersion')
            
            print(f"   ✅ GitHub Raw URL 请求成功")
            print(f"   - 更新时间: {last_updated}")
            print(f"   - 缓存版本: {cache_version}")
            print(f"   - Commit SHA: {commit_sha}")
            
            if commit_sha != expected_commit_sha:
                print(f"   ⚠️  Commit SHA 不匹配！")
                print(f"      - 期望: {expected_commit_sha}")
                print(f"      - 实际: {commit_sha}")
        else:
            print(f"   ❌ GitHub Raw URL 请求失败: HTTP {response.status_code}")
            commit_sha = None
    except Exception as e:
        print(f"   ❌ GitHub Raw URL 请求失败: {e}")
        commit_sha = None
    
    # 步骤2: 使用 commit SHA 从 CDN 获取数据（模拟前端步骤2）
    if commit_sha:
        print(f"\n3. 步骤2: 使用 commit SHA 从 CDN 获取数据...")
        
        # 原始 URL（前端配置中的 @main）
        original_url = "https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/videos.json"
        print(f"   原始 URL（前端配置）: {original_url}")
        
        # 替换后的 URL（应该使用的）
        replaced_url = original_url.replace("@main", f"@{commit_sha}")
        print(f"   替换后 URL（实际请求）: {replaced_url}")
        
        try:
            response = requests.get(replaced_url, timeout=10)
            if response.status_code == 200:
                cdn_data = response.json()
                cdn_last_updated = cdn_data.get('lastUpdated')
                cdn_cache_version = cdn_data.get('cacheVersion')
                
                print(f"   ✅ CDN 请求成功")
                print(f"   - 更新时间: {cdn_last_updated}")
                print(f"   - 缓存版本: {cdn_cache_version}")
                
                # 验证数据是否一致
                if (cdn_last_updated == last_updated and 
                    cdn_cache_version == cache_version):
                    print(f"   ✅ CDN 数据与 GitHub Raw URL 数据一致")
                    
                    # 验证是否是最新数据
                    if (cdn_last_updated == local_last_updated and 
                        cdn_cache_version == local_cache_version):
                        print(f"   ✅ CDN 数据是最新的（与本地一致）")
                        return True
                    else:
                        print(f"   ⚠️  CDN 数据不是最新的")
                        print(f"      - 本地: {local_last_updated} / {local_cache_version}")
                        print(f"      - CDN:  {cdn_last_updated} / {cdn_cache_version}")
                else:
                    print(f"   ❌ CDN 数据与 GitHub Raw URL 数据不一致")
                    print(f"      - GitHub: {last_updated} / {cache_version}")
                    print(f"      - CDN:    {cdn_last_updated} / {cdn_cache_version}")
            else:
                print(f"   ❌ CDN 请求失败: HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ CDN 请求失败: {e}")
    else:
        print(f"\n3. 步骤2: 跳过（未获取到 commit SHA）")
    
    # 测试使用 @main 的 URL（对比）
    print(f"\n4. 对比测试: 使用 @main 的 URL...")
    try:
        main_url = "https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/videos.json"
        response = requests.get(main_url, timeout=10)
        if response.status_code == 200:
            main_data = response.json()
            main_last_updated = main_data.get('lastUpdated')
            main_cache_version = main_data.get('cacheVersion')
            
            print(f"   ✅ @main URL 请求成功")
            print(f"   - 更新时间: {main_last_updated}")
            print(f"   - 缓存版本: {main_cache_version}")
            
            if (main_last_updated == local_last_updated and 
                main_cache_version == local_cache_version):
                print(f"   ⚠️  @main 返回的是最新数据（不应该）")
            else:
                print(f"   ✅ @main 返回的是旧数据（预期）")
                print(f"      - 本地: {local_last_updated} / {local_cache_version}")
                print(f"      - @main: {main_last_updated} / {main_cache_version}")
    except Exception as e:
        print(f"   ❌ @main URL 请求失败: {e}")
    
    return False

if __name__ == "__main__":
    success = test_frontend_behavior()
    exit(0 if success else 1)

