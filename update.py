#!/usr/bin/env python3
"""
视频库自动更新脚本
自动扫描videos和thumbnails文件夹，更新videos.json配置文件
"""

import os
import json
import glob
from datetime import datetime
from pathlib import Path

class VideoLibraryUpdater:
    def __init__(self, repo_path="."):
        self.repo_path = Path(repo_path)
        self.videos_path = self.repo_path / "videos"
        self.thumbnails_path = self.repo_path / "thumbnails"
        self.json_path = self.repo_path / "videos.json"
        
    def get_video_files(self):
        """获取所有视频文件"""
        video_extensions = ['*.mp4', '*.MP4', '*.mov', '*.MOV', '*.avi', '*.AVI', '*.mkv', '*.MKV']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(glob.glob(str(self.videos_path / ext)))
        
        return [Path(f).name for f in video_files]
    
    def get_thumbnail_files(self):
        """获取所有缩略图文件"""
        thumbnail_extensions = ['*.jpg', '*.JPG', '*.jpeg', '*.JPEG', '*.png', '*.PNG', '*.webp', '*.WEBP']
        thumbnail_files = []
        
        for ext in thumbnail_extensions:
            thumbnail_files.extend(glob.glob(str(self.thumbnails_path / ext)))
        
        return {Path(f).stem: Path(f).name for f in thumbnail_files}
    
    def get_file_size(self, filename):
        """获取文件大小（MB）"""
        file_path = self.videos_path / filename
        if file_path.exists():
            size_bytes = file_path.stat().st_size
            return round(size_bytes / (1024 * 1024), 1)
        return 0
    
    def estimate_duration(self, filename):
        """根据文件名或文件大小估算视频时长（这里需要你根据实际情况调整）"""
        # 这里只是一个简单的估算，你可以根据实际视频调整
        size_mb = self.get_file_size(filename)
        
        # 简单的估算逻辑：假设1MB约等于5秒视频（根据你的视频压缩率调整）
        estimated_seconds = int(size_mb * 5)
        
        if estimated_seconds < 60:
            return f"0:{estimated_seconds:02d}"
        else:
            minutes = estimated_seconds // 60
            seconds = estimated_seconds % 60
            return f"{minutes}:{seconds:02d}"
    
    def generate_video_data(self, video_files, thumbnails):
        """生成视频数据"""
        videos = []
        
        for i, video_file in enumerate(sorted(video_files), 1):
            # 获取文件名（不含扩展名）
            name_without_ext = Path(video_file).stem
            
            # 生成标题（将文件名转换为友好名称）
            title = self.generate_friendly_title(name_without_ext)
            
            # 生成描述
            description = self.generate_description(title)
            
            # 获取对应的缩略图
            thumbnail = thumbnails.get(name_without_ext, "")
            if thumbnail:
                thumbnail_url = f"https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/thumbnails/{thumbnail}"
            else:
                thumbnail_url = ""
            
            video_data = {
                "id": i,
                "title": title,
                "filename": video_file,
                "url": f"https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/videos/{video_file}",
                "description": description,
                "duration": self.estimate_duration(video_file),
                "size": f"{self.get_file_size(video_file)} MB",
                "thumbnail": thumbnail_url,
                "createdAt": datetime.now().strftime("%Y-%m-%d")
            }
            
            videos.append(video_data)
        
        return videos
    
    def generate_friendly_title(self, filename):
        """生成友好的视频标题"""
        # 移除常见的文件前缀和后缀
        name = filename.replace('_', ' ').replace('-', ' ')
        
        # 特殊文件名处理
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
        
        # 默认情况：将文件名转换为标题格式
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
    
    def load_existing_data(self):
        """加载现有的videos.json数据"""
        if self.json_path.exists():
            with open(self.json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def update_videos_json(self):
        """更新videos.json文件"""
        print("开始扫描视频文件...")
        
        # 检查videos文件夹是否存在
        if not self.videos_path.exists():
            print(f"错误: videos文件夹不存在: {self.videos_path}")
            return False
        
        # 获取文件列表
        video_files = self.get_video_files()
        thumbnails = self.get_thumbnail_files()
        
        if not video_files:
            print("警告: 在videos文件夹中没有找到视频文件")
            return False
        
        print(f"找到 {len(video_files)} 个视频文件:")
        for video in video_files:
            print(f"  - {video}")
        
        print(f"找到 {len(thumbnails)} 个缩略图文件")
        
        # 生成视频数据
        videos = self.generate_video_data(video_files, thumbnails)
        
        # 加载现有数据（保留自定义字段）
        existing_data = self.load_existing_data()
        
        # 合并数据
        updated_data = {
            "videos": videos,
            "total": len(videos),
            "lastUpdated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "repository": "https://github.com/yezhu9181/my-video-host"
        }
        
        # 保留现有的自定义字段
        if existing_data:
            for key, value in existing_data.items():
                if key not in updated_data:
                    updated_data[key] = value
        
        # 写入文件
        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n✅ 成功更新 videos.json")
            print(f"📊 统计信息:")
            print(f"   - 视频数量: {len(videos)}")
            print(f"   - 最后更新: {updated_data['lastUpdated']}")
            print(f"   - 输出文件: {self.json_path}")
            
            # 显示生成的视频列表
            print(f"\n📹 视频列表:")
            for video in videos:
                print(f"   - {video['title']} ({video['filename']})")
            
            return True
            
        except Exception as e:
            print(f"❌ 写入文件失败: {e}")
            return False

def main():
    """主函数"""
    print("🎬 视频库自动更新脚本")
    print("=" * 50)
    
    # 初始化更新器
    updater = VideoLibraryUpdater()
    
    # 执行更新
    success = updater.update_videos_json()
    
    if success:
        print("\n🎉 更新完成！")
        print("\n💡 下一步:")
        print("   1. 检查生成的 videos.json 文件")
        print("   2. 提交更改到GitHub: git add videos.json")
        print("   3. 推送: git commit -m '更新视频列表' && git push")
    else:
        print("\n❌ 更新失败，请检查错误信息")

if __name__ == "__main__":
    main()