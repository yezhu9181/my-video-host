#!/usr/bin/env python3
"""
视频库自动更新脚本 - 支持分页版本
"""

import os
import json
import glob
from datetime import datetime
from pathlib import Path

class VideoLibraryUpdater:
    def __init__(self, repo_path=".", page_size=10):
        self.repo_path = Path(repo_path)
        self.videos_path = self.repo_path / "videos"
        self.thumbnails_path = self.repo_path / "thumbnails"
        self.json_path = self.repo_path / "videos.json"
        self.page_size = page_size
        
        self.thumbnails_path.mkdir(exist_ok=True)
        
    def get_video_files(self):
        """获取所有视频文件"""
        video_extensions = ['*.mp4', '*.MP4', '*.mov', '*.MOV', '*.avi', '*.AVI', '*.mkv', '*.MKV', '*.webm', '*.WEBM']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(glob.glob(str(self.videos_path / ext)))
        
        return [Path(f).name for f in video_files]
    
    def create_svg_thumbnail(self, video_filename, file_size_mb):
        """创建SVG缩略图"""
        thumbnail_name = Path(video_filename).stem + ".svg"
        thumbnail_path = self.thumbnails_path / thumbnail_name
        
        try:
            title = self.generate_friendly_title(Path(video_filename).stem)
            file_extension = Path(video_filename).suffix.upper()
            
            # 颜色方案
            if file_size_mb > 50:
                color_scheme = {"bg": "#4C1D95", "primary": "#8B5CF6", "secondary": "#C4B5FD"}
            elif file_size_mb > 20:
                color_scheme = {"bg": "#065F46", "primary": "#10B981", "secondary": "#6EE7B7"}
            else:
                color_scheme = {"bg": "#1E40AF", "primary": "#3B82F6", "secondary": "#93C5FD"}
            
            svg_content = f'''<svg width="320" height="180" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{color_scheme['bg']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1F2937;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bgGradient)" rx="8" ry="8"/>
  <g transform="translate(160, 70)">
    <circle r="28" fill="{color_scheme['primary']}" fill-opacity="0.9"/>
    <polygon points="-8,-10 -8,10 12,0" fill="#FFFFFF"/>
  </g>
  <g transform="translate(160, 120)">
    <text text-anchor="middle" fill="#F9FAFB" font-family="Arial, sans-serif" font-size="14" font-weight="bold">
      {title}
    </text>
    <text y="20" text-anchor="middle" fill="{color_scheme['secondary']}" font-family="Arial, sans-serif" font-size="11">
      {file_extension} • {file_size_mb} MB
    </text>
  </g>
</svg>'''
            
            with open(thumbnail_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            
            return thumbnail_name
            
        except Exception as e:
            print(f"  ❌ 创建SVG缩略图失败: {e}")
            return ""
    
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
        estimated_seconds = int(size_mb / 0.25)  # 假设编码率为 2 Mbps
        estimated_seconds = min(estimated_seconds, 3600)
        
        if estimated_seconds < 60:
            return f"0:{estimated_seconds:02d}"
        else:
            minutes = estimated_seconds // 60
            seconds = estimated_seconds % 60
            return f"{minutes}:{seconds:02d}"
    
    def generate_video_data(self, video_files):
        """生成视频数据"""
        videos = []
        
        for i, video_file in enumerate(sorted(video_files), 1):
            print(f"📹 处理视频 {i}/{len(video_files)}: {video_file}")
            
            name_without_ext = Path(video_file).stem
            title = self.generate_friendly_title(name_without_ext)
            description = self.generate_description(title)
            file_size = self.get_file_size(video_file)
            
            # 创建SVG缩略图
            thumbnail_filename = self.create_svg_thumbnail(video_file, file_size)
            thumbnail_url = f"https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/thumbnails/{thumbnail_filename}" if thumbnail_filename else ""
            
            duration = self.estimate_duration(video_file)
            resolution = self.get_video_dimensions_from_filename(video_file)
            
            video_data = {
                "id": i,
                "title": title,
                "filename": video_file,
                "url": f"https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/videos/{video_file}",
                "description": description,
                "duration": duration,
                "size": f"{file_size} MB",
                "thumbnail": thumbnail_url,
                "codec": "H.264",
                "resolution": resolution,
                "createdAt": datetime.now().strftime("%Y-%m-%d"),
                "thumbnailType": "SVG"
            }
            
            videos.append(video_data)
        
        return videos
    
    def get_video_dimensions_from_filename(self, filename):
        """从文件名猜测视频分辨率"""
        name_lower = filename.lower()
        
        if any(x in name_lower for x in ['4k', '2160p', 'uhd']):
            return "3840x2160"
        elif any(x in name_lower for x in ['2k', '1440p']):
            return "2560x1440"
        elif any(x in name_lower for x in ['1080p', 'fullhd']):
            return "1920x1080"
        elif any(x in name_lower for x in ['720p', 'hd']):
            return "1280x720"
        else:
            size_mb = self.get_file_size(filename)
            if size_mb > 100:
                return "1920x1080"
            elif size_mb > 50:
                return "1280x720"
            else:
                return "854x480"
    
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
        """更新videos.json文件（单页版本）"""
        print("🎬 视频库更新脚本 - 分页支持版本")
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
        
        # 计算分页信息
        total_videos = len(videos)
        total_pages = (total_videos + self.page_size - 1) // self.page_size
        
        # 创建JSON数据（单页版本）
        updated_data = {
            "videos": videos,  # 所有视频在一页中
            "pagination": {
                "total": total_videos,
                "page": 1,
                "pageSize": self.page_size,
                "totalPages": total_pages,
                "hasNext": False,
                "hasPrev": False
            },
            "lastUpdated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "repository": "https://github.com/yezhu9181/my-video-host",
            "apiEndpoints": {
                "allVideos": "/videos.json",
                "paginated": "/videos.json?page={page}&limit={limit}",
                "search": "/videos.json?search={keyword}",
                "byId": "/videos.json?id={id}"
            }
        }
        
        # 写入文件
        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 成功更新 videos.json")
            print(f"📊 分页信息:")
            print(f"   - 总视频数: {total_videos}")
            print(f"   - 每页数量: {self.page_size}")
            print(f"   - 总页数: {total_pages}")
            
            return True
            
        except Exception as e:
            print(f"❌ 写入文件失败: {e}")
            return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description='更新视频库配置')
    parser.add_argument('--page-size', type=int, default=10, help='每页显示的视频数量')
    
    args = parser.parse_args()
    
    updater = VideoLibraryUpdater(page_size=args.page_size)
    success = updater.update_videos_json()
    
    if success:
        print("\n🎉 更新完成！支持分页API")
        print("\n🔗 API端点:")
        print("   - GET /videos.json (获取所有视频)")
        print("   - GET /videos.json?page=1&limit=10 (分页获取)")
        print("   - GET /videos.json?search=关键词 (搜索视频)")
        print("   - GET /videos.json?id=1 (根据ID获取)")
    else:
        print("\n❌ 更新失败")

if __name__ == "__main__":
    main()