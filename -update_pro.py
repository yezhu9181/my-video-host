#!/usr/bin/env python3
"""
视频库自动更新脚本 - 修复缩略图提取问题
"""

import os
import json
import glob
import subprocess
from datetime import datetime
from pathlib import Path

class VideoLibraryUpdater:
    def __init__(self, repo_path="."):
        self.repo_path = Path(repo_path)
        self.videos_path = self.repo_path / "videos"
        self.thumbnails_path = self.repo_path / "thumbnails"
        self.json_path = self.repo_path / "videos.json"
        
        self.thumbnails_path.mkdir(exist_ok=True)
        
    def get_video_files(self):
        """获取所有视频文件"""
        video_extensions = ['*.mp4', '*.MP4', '*.mov', '*.MOV', '*.avi', '*.AVI', '*.mkv', '*.MKV', '*.webm', '*.WEBM']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(glob.glob(str(self.videos_path / ext)))
        
        return [Path(f).name for f in video_files]
    
    def debug_video_info(self, video_filename):
        """调试视频文件信息"""
        video_path = self.videos_path / video_filename
        print(f"  🔍 视频文件信息:")
        print(f"     路径: {video_path}")
        print(f"     存在: {video_path.exists()}")
        print(f"     大小: {video_path.stat().st_size if video_path.exists() else 0} bytes")
    
    def extract_thumbnail_improved(self, video_filename):
        """改进的缩略图提取方法"""
        video_path = self.videos_path / video_filename
        thumbnail_name = Path(video_filename).stem + ".jpg"
        thumbnail_path = self.thumbnails_path / thumbnail_name
        
        # 先调试视频文件
        self.debug_video_info(video_filename)
        
        # 尝试不同的时间点提取
        time_points = ['00:00:01', '00:00:03', '00:00:05', '00:00:10']
        
        for time_point in time_points:
            print(f"  🎞️ 尝试在 {time_point} 提取缩略图...")
            
            try:
                # 方法1: 使用更简单的命令
                cmd1 = [
                    'ffmpeg',
                    '-i', str(video_path),
                    '-ss', time_point,           #  seek到指定时间
                    '-vframes', '1',             # 只取一帧
                    '-q:v', '2',                 # 图像质量
                    '-f', 'image2',              # 强制输出格式
                    '-y',                        # 覆盖输出
                    str(thumbnail_path)
                ]
                
                # 方法2: 备用命令（不同的参数）
                cmd2 = [
                    'ffmpeg',
                    '-i', str(video_path),
                    '-ss', time_point,
                    '-vframes', '1',
                    '-vf', 'scale=320:180',      # 缩放尺寸
                    '-qscale:v', '2',
                    '-y',
                    str(thumbnail_path)
                ]
                
                # 先尝试方法1
                result = subprocess.run(cmd1, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    if thumbnail_path.exists():
                        file_size = thumbnail_path.stat().st_size
                        if file_size > 0:
                            print(f"  ✅ 成功在 {time_point} 提取缩略图: {thumbnail_name} ({file_size} bytes)")
                            
                            # 验证图片是否有效
                            try:
                                # 尝试读取图片文件头
                                with open(thumbnail_path, 'rb') as f:
                                    header = f.read(10)
                                    if header.startswith(b'\xff\xd8\xff'):  # JPEG文件头
                                        print(f"  ✅ 缩略图验证: 有效的JPEG文件")
                                        return thumbnail_name
                                    else:
                                        print(f"  ❌ 缩略图验证: 不是有效的JPEG文件")
                                        os.remove(thumbnail_path)  # 删除无效文件
                                        continue
                            except:
                                print(f"  ❌ 无法验证缩略图文件")
                                continue
                        else:
                            print(f"  ❌ 缩略图文件大小为0")
                            if thumbnail_path.exists():
                                os.remove(thumbnail_path)
                            continue
                    else:
                        print(f"  ❌ 缩略图文件未创建")
                        continue
                else:
                    print(f"  ❌ 方法1失败，尝试方法2...")
                    
                    # 尝试方法2
                    result = subprocess.run(cmd2, capture_output=True, text=True, timeout=30)
                    if result.returncode == 0 and thumbnail_path.exists():
                        file_size = thumbnail_path.stat().st_size
                        if file_size > 0:
                            print(f"  ✅ 方法2成功在 {time_point} 提取缩略图")
                            return thumbnail_name
                        else:
                            print(f"  ❌ 方法2文件大小为0")
                            if thumbnail_path.exists():
                                os.remove(thumbnail_path)
                            continue
                    else:
                        print(f"  ❌ 方法2也失败")
                        if thumbnail_path.exists():
                            os.remove(thumbnail_path)
                        continue
                        
            except subprocess.TimeoutExpired:
                print(f"  ⏰ 提取超时")
                continue
            except Exception as e:
                print(f"  ❌ 提取错误: {e}")
                continue
        
        print(f"  ❌ 所有时间点都失败，无法提取缩略图")
        return ""
    
    def create_fallback_thumbnail(self, video_filename):
        """创建备用SVG缩略图"""
        thumbnail_name = Path(video_filename).stem + ".svg"
        thumbnail_path = self.thumbnails_path / thumbnail_name
        
        try:
            title = self.generate_friendly_title(Path(video_filename).stem)
            svg_content = f'''<svg width="320" height="180" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#4A5568;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#2D3748;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#grad1)"/>
  <circle cx="160" cy="70" r="25" fill="none" stroke="#CBD5E0" stroke-width="3"/>
  <polygon points="150,60 150,80 170,70" fill="#CBD5E0"/>
  <text x="160" y="110" text-anchor="middle" fill="#F7FAFC" font-family="Arial, sans-serif" font-size="16" font-weight="bold">
    {title}
  </text>
  <text x="160" y="130" text-anchor="middle" fill="#CBD5E0" font-family="Arial, sans-serif" font-size="12">
    {Path(video_filename).name}
  </text>
  <text x="160" y="150" text-anchor="middle" fill="#718096" font-family="Arial, sans-serif" font-size="10">
    点击播放视频
  </text>
</svg>'''
            
            with open(thumbnail_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            
            print(f"  🎨 创建备用SVG缩略图: {thumbnail_name}")
            return thumbnail_name
            
        except Exception as e:
            print(f"  ❌ 创建SVG缩略图失败: {e}")
            return ""
    
    def check_ffmpeg_available(self):
        """检查ffmpeg是否可用"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("✅ FFmpeg可用")
                return True
            else:
                print("❌ FFmpeg不可用")
                return False
        except Exception as e:
            print(f"❌ FFmpeg检查失败: {e}")
            return False
    
    def get_video_info(self, video_filename):
        """获取视频详细信息"""
        video_path = self.videos_path / video_filename
        
        try:
            # 获取视频时长和编码信息
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                info = json.loads(result.stdout)
                
                # 提取时长
                duration = float(info['format']['duration'])
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                
                # 提取视频流信息
                video_stream = None
                for stream in info['streams']:
                    if stream['codec_type'] == 'video':
                        video_stream = stream
                        break
                
                return {
                    'duration': f"{minutes}:{seconds:02d}",
                    'codec': video_stream['codec_name'] if video_stream else 'unknown',
                    'width': video_stream.get('width', 0) if video_stream else 0,
                    'height': video_stream.get('height', 0) if video_stream else 0
                }
        except Exception as e:
            print(f"  ⚠️  无法获取视频详细信息: {e}")
        
        # 备用方案
        return {
            'duration': self.estimate_duration(video_filename),
            'codec': 'unknown',
            'width': 0,
            'height': 0
        }
    
    def get_file_size(self, filename):
        """获取文件大小（MB）"""
        file_path = self.videos_path / filename
        if file_path.exists():
            size_bytes = file_path.stat().st_size
            return round(size_bytes / (1024 * 1024), 1)
        return 0
    
    def estimate_duration(self, filename):
        """估算视频时长"""
        size_mb = self.get_file_size(filename)
        estimated_seconds = min(int(size_mb * 5), 600)
        
        if estimated_seconds < 60:
            return f"0:{estimated_seconds:02d}"
        else:
            minutes = estimated_seconds // 60
            seconds = estimated_seconds % 60
            return f"{minutes}:{seconds:02d}"
    
    def generate_video_data(self, video_files):
        """生成视频数据"""
        videos = []
        ffmpeg_available = self.check_ffmpeg_available()
        
        for i, video_file in enumerate(sorted(video_files), 1):
            print(f"\n📹 处理视频 {i}/{len(video_files)}: {video_file}")
            print("-" * 50)
            
            name_without_ext = Path(video_file).stem
            title = self.generate_friendly_title(name_without_ext)
            description = self.generate_description(title)
            
            # 获取视频信息
            video_info = self.get_video_info(video_file) if ffmpeg_available else {
                'duration': self.estimate_duration(video_file),
                'codec': 'unknown'
            }
            
            # 提取缩略图
            thumbnail_filename = ""
            if ffmpeg_available:
                print("  🔄 尝试提取视频帧作为缩略图...")
                thumbnail_filename = self.extract_thumbnail_improved(video_file)
            
            # 如果提取失败，使用SVG备用方案
            if not thumbnail_filename:
                print("  🔄 使用备用SVG缩略图...")
                thumbnail_filename = self.create_fallback_thumbnail(video_file)
            
            # 生成缩略图URL
            if thumbnail_filename:
                thumbnail_url = f"https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/thumbnails/{thumbnail_filename}"
                print(f"  🌐 缩略图URL: {thumbnail_url}")
            else:
                thumbnail_url = ""
                print(f"  ❌ 无法生成任何缩略图")
            
            file_size = self.get_file_size(video_file)
            
            video_data = {
                "id": i,
                "title": title,
                "filename": video_file,
                "url": f"https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/videos/{video_file}",
                "description": description,
                "duration": video_info['duration'],
                "size": f"{file_size} MB",
                "thumbnail": thumbnail_url,
                "codec": video_info['codec'],
                "resolution": f"{video_info['width']}x{video_info['height']}" if video_info['width'] else "unknown",
                "createdAt": datetime.now().strftime("%Y-%m-%d")
            }
            
            videos.append(video_data)
            print(f"  ✅ 完成: {title}")
        
        return videos
    
    def generate_friendly_title(self, filename):
        """生成友好的视频标题"""
        name = filename.replace('_', ' ').replace('-', ' ')
        
        name_mapping = {
            "intro": "产品介绍视频",
            "tutorial": "使用教程",
            "demo": "功能演示",
            "guide": "操作指南",
            "overview": "系统概览"
        }
        
        for key, value in name_mapping.items():
            if key in filename.lower():
                return value
        
        return name.title()
    
    def generate_description(self, title):
        """根据标题生成描述"""
        descriptions = {
            "产品介绍视频": "全面介绍产品的功能特性和使用场景",
            "使用教程": "详细的使用方法和操作步骤说明",
            "功能演示": "核心功能的实际使用演示",
            "操作指南": "具体的操作流程和注意事项",
            "系统概览": "系统整体架构和主要模块介绍"
        }
        
        return descriptions.get(title, f"这是关于{title}的详细说明视频")
    
    def update_videos_json(self):
        """更新videos.json文件"""
        print("🎬 视频库更新脚本 - 修复版")
        print("=" * 60)
        
        if not self.videos_path.exists():
            print(f"❌ 错误: videos文件夹不存在")
            return False
        
        video_files = self.get_video_files()
        if not video_files:
            print("❌ 错误: 没有找到视频文件")
            return False
        
        print(f"📁 找到 {len(video_files)} 个视频文件")
        
        videos = self.generate_video_data(video_files)
        
        # 创建JSON数据
        updated_data = {
            "videos": videos,
            "total": len(videos),
            "lastUpdated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "repository": "https://github.com/yezhu9181/my-video-host"
        }
        
        # 写入文件
        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, ensure_ascii=False, indent=2)
            
            print("\n" + "=" * 60)
            print(f"✅ 成功更新 videos.json")
            
            # 统计信息
            jpg_count = sum(1 for v in videos if v['thumbnail'] and '.jpg' in v['thumbnail'])
            svg_count = sum(1 for v in videos if v['thumbnail'] and '.svg' in v['thumbnail'])
            
            print(f"📊 统计信息:")
            print(f"   - 视频数量: {len(videos)}")
            print(f"   - JPG缩略图: {jpg_count}")
            print(f"   - SVG缩略图: {svg_count}")
            print(f"   - 无缩略图: {len(videos) - jpg_count - svg_count}")
            
            print(f"\n📹 视频列表:")
            for video in videos:
                if '.jpg' in video['thumbnail']:
                    status = "🖼️ "
                elif '.svg' in video['thumbnail']:
                    status = "🎨"
                else:
                    status = "❌"
                print(f"   {status} {video['title']} ({video['duration']}, {video['size']})")
            
            return True
            
        except Exception as e:
            print(f"❌ 写入文件失败: {e}")
            return False

def main():
    updater = VideoLibraryUpdater()
    success = updater.update_videos_json()
    
    if success:
        print("\n🎉 更新完成！")
        print("\n💡 如果缩略图不是视频第一帧，请检查:")
        print("   1. 视频文件是否损坏")
        print("   2. FFmpeg版本是否支持该视频格式")
        print("   3. 尝试手动命令: ffmpeg -i videos/文件名 -ss 00:00:01 -vframes 1 thumbnails/输出.jpg")
    else:
        print("\n❌ 更新失败")

if __name__ == "__main__":
    main()