#!/usr/bin/env python3
"""
测试前端行为：直接使用 @main 的 URL 是否能获取最新数据
"""

import json
import requests
import time
from pathlib import Path

def test_frontend_behavior():
    """测试直接使用 @main 的 URL 是否能获取最新数据"""
    print("=" * 60)
    print("测试前端行为：直接使用 @main 的 URL")
    print("=" * 60)
    
    # 读取本地文件
    local_file = Path("videos.json")
    with open(local_file, 'r', encoding='utf-8') as f:
        local_data = json.load(f)
    
    local_last_updated = local_data.get('lastUpdated')
    local_cache_version = local_data.get('cacheVersion')
    
    print(f"\n1. 本地数据:")
    print(f"   - 更新时间: {local_last_updated}")
    print(f"   - 缓存版本: {local_cache_version}")
    
    # 测试使用 @main 的 URL（前端配置中的 URL）
    print(f"\n2. 测试使用 @main 的 URL（前端配置）...")
    cdn_url = "https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/videos.json"
    print(f"   URL: {cdn_url}")
    
    max_attempts = 5
    success = False
    
    for attempt in range(1, max_attempts + 1):
        # 使用不同的缓存破坏参数
        cache_buster = f"?v={int(time.time())}&_t={time.time()}&attempt={attempt}&nocache=1&_cb={time.time()}"
        test_url = f"{cdn_url}{cache_buster}"
        
        print(f"\n   尝试 {attempt}/{max_attempts}: {test_url}")
        
        try:
            response = requests.get(test_url, 
                                  headers={
                                      'Cache-Control': 'no-cache, no-store, must-revalidate, proxy-revalidate, max-age=0',
                                      'Pragma': 'no-cache',
                                      'Expires': '0',
                                      'If-Modified-Since': 'Thu, 01 Jan 1970 00:00:00 GMT',
                                      'If-None-Match': '*',
                                      'X-Requested-With': 'XMLHttpRequest'
                                  },
                                  timeout=10)
            
            # 处理 304 Not Modified - 尝试强制刷新
            if response.status_code == 304:
                print(f"   ⚠️  HTTP 304 Not Modified，尝试强制刷新...")
                # 使用不同的 URL 参数强制刷新
                force_refresh_url = f"{cdn_url}?t={int(time.time() * 1000)}&_force_refresh=1&_nocache={int(time.time())}"
                response = requests.get(force_refresh_url,
                                      headers={
                                          'Cache-Control': 'no-cache, no-store, must-revalidate',
                                          'Pragma': 'no-cache',
                                          'Expires': '0'
                                      },
                                      timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                cdn_last_updated = data.get('lastUpdated')
                cdn_cache_version = data.get('cacheVersion')
                
                print(f"   ✅ CDN 请求成功")
                print(f"   - 更新时间: {cdn_last_updated}")
                print(f"   - 缓存版本: {cdn_cache_version}")
                
                # 比较数据是否一致
                if (cdn_last_updated == local_last_updated and 
                    cdn_cache_version == local_cache_version):
                    print(f"\n   ✅ 数据一致！使用 @main 的 URL 返回的是最新数据")
                    success = True
                    break
                else:
                    print(f"\n   ⚠️  数据不一致（尝试 {attempt}/{max_attempts}）")
                    print(f"      - 本地: {local_last_updated} / {local_cache_version}")
                    print(f"      - CDN:  {cdn_last_updated} / {cdn_cache_version}")
                    if attempt < max_attempts:
                        print(f"      - 等待 3 秒后重试...")
                        time.sleep(3)
            else:
                print(f"   ❌ HTTP {response.status_code}: {response.reason if hasattr(response, 'reason') else 'Unknown'}")
                
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
            if attempt < max_attempts:
                print(f"      - 等待 3 秒后重试...")
                time.sleep(3)
    
    # 总结
    print(f"\n3. 测试总结:")
    print("=" * 60)
    if success:
        print("✅ 测试通过：使用 @main 的 URL 可以获取到最新数据")
        print("💡 说明：CDN 缓存已更新，或者缓存破坏参数生效")
    else:
        print("❌ 测试失败：使用 @main 的 URL 无法获取到最新数据")
        print("💡 问题：CDN 缓存可能尚未更新")
        print("💡 建议：")
        print("   1. 等待几分钟后重试（CDN 缓存可能需要时间更新）")
        print("   2. 清除 CDN 缓存（如果支持）")
        print("   3. 使用 commit SHA 替换 @main（推荐方案）")
    
    return success

if __name__ == "__main__":
    success = test_frontend_behavior()
    exit(0 if success else 1)
