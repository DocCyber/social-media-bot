#!/usr/bin/env python3
"""
Smart Timing Optimization System
Analyzes engagement patterns and optimizes posting schedules across platforms.
"""

import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import sys

sys.path.append(str(Path(__file__).parent.parent))

from utils.date_aware_logger import get_enhanced_logger
from utils.monitoring import record_metric
from utils.config_manager import ConfigManager

class EngagementAnalyzer:
    def __init__(self):
        self.logger = get_enhanced_logger("timing_optimizer", enable_background_markers=False)
        self.config_manager = ConfigManager()
        self.engagement_data = self._load_engagement_data()
        
    def _load_engagement_data(self) -> Dict[str, List[Dict]]:
        """Load historical engagement data for analysis."""
        data_file = Path(__file__).parent / "engagement_history.json"
        
        if data_file.exists():
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading engagement data: {e}")
        
        return {"twitter": [], "mastodon": [], "bluesky": []}
    
    def record_engagement(self, platform: str, post_time: datetime, 
                         likes: int = 0, reposts: int = 0, replies: int = 0):
        """Record engagement metrics for a post."""
        engagement_score = likes + (reposts * 2) + (replies * 3)  # Weighted scoring
        
        engagement_record = {
            "timestamp": post_time.isoformat(),
            "hour": post_time.hour,
            "day_of_week": post_time.weekday(),
            "likes": likes,
            "reposts": reposts,
            "replies": replies,
            "engagement_score": engagement_score
        }
        
        if platform not in self.engagement_data:
            self.engagement_data[platform] = []
        
        self.engagement_data[platform].append(engagement_record)
        
        # Save updated data
        self._save_engagement_data()
        
        # Record metrics
        record_metric("engagement_recorded", 1, "timing_optimizer", 
                     {"platform": platform})
        record_metric("engagement_score", engagement_score, "timing_optimizer", 
                     {"platform": platform})
    
    def _save_engagement_data(self):
        """Save engagement data to file."""
        data_file = Path(__file__).parent / "engagement_history.json"
        
        try:
            # Keep only last 1000 records per platform to prevent file bloat
            for platform in self.engagement_data:
                if len(self.engagement_data[platform]) > 1000:
                    self.engagement_data[platform] = self.engagement_data[platform][-1000:]
            
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(self.engagement_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving engagement data: {e}")
    
    def get_optimal_hours(self, platform: str, num_hours: int = 3) -> List[int]:
        """Get optimal posting hours based on historical engagement."""
        if platform not in self.engagement_data or not self.engagement_data[platform]:
            # Default optimal hours if no data
            defaults = {
                "twitter": [9, 12, 18],
                "mastodon": [10, 15, 20],
                "bluesky": [8, 14, 19]
            }
            return defaults.get(platform, [9, 15, 21])
        
        # Analyze engagement by hour
        hourly_scores = defaultdict(list)
        
        for record in self.engagement_data[platform]:
            hour = record["hour"]
            score = record["engagement_score"]
            hourly_scores[hour].append(score)
        
        # Calculate average engagement per hour
        hourly_averages = {}
        for hour, scores in hourly_scores.items():
            hourly_averages[hour] = statistics.mean(scores) if scores else 0
        
        # Get top performing hours
        sorted_hours = sorted(hourly_averages.items(), key=lambda x: x[1], reverse=True)
        optimal_hours = [hour for hour, _ in sorted_hours[:num_hours]]
        
        # Ensure we have at least the requested number of hours
        if len(optimal_hours) < num_hours:
            # Fill with default hours not already selected
            default_hours = [9, 12, 15, 18, 21]
            for hour in default_hours:
                if hour not in optimal_hours and len(optimal_hours) < num_hours:
                    optimal_hours.append(hour)
        
        optimal_hours.sort()
        
        self.logger.info(f"Optimal hours for {platform}: {optimal_hours}")
        return optimal_hours
    
    def get_optimal_days(self, platform: str) -> List[int]:
        """Get optimal days of week based on engagement (0=Monday, 6=Sunday)."""
        if platform not in self.engagement_data or not self.engagement_data[platform]:
            return list(range(7))  # All days if no data
        
        # Analyze engagement by day of week
        daily_scores = defaultdict(list)
        
        for record in self.engagement_data[platform]:
            day = record["day_of_week"]
            score = record["engagement_score"]
            daily_scores[day].append(score)
        
        # Calculate average engagement per day
        daily_averages = {}
        for day, scores in daily_scores.items():
            daily_averages[day] = statistics.mean(scores) if scores else 0
        
        # Filter days with above-average engagement
        if daily_averages:
            overall_avg = statistics.mean(daily_averages.values())
            optimal_days = [day for day, avg in daily_averages.items() if avg >= overall_avg]
        else:
            optimal_days = list(range(7))
        
        # Ensure at least 3 days
        if len(optimal_days) < 3:
            optimal_days = sorted(daily_averages.keys())[:5]
        
        return sorted(optimal_days)

class SmartScheduleOptimizer:
    def __init__(self):
        self.logger = get_enhanced_logger("schedule_optimizer", enable_background_markers=False)
        self.config_manager = ConfigManager()
        self.analyzer = EngagementAnalyzer()
        
    def generate_optimal_schedule(self, platform: str) -> Dict[str, str]:
        """Generate optimal cron schedules for a platform."""
        optimal_hours = self.analyzer.get_optimal_hours(platform, 3)
        optimal_days = self.analyzer.get_optimal_days(platform)
        
        # Convert days to cron format (0=Sunday in cron, 0=Monday in Python)
        cron_days = [(day + 1) % 7 for day in optimal_days]
        cron_days_str = ','.join(map(str, sorted(cron_days)))
        
        # Create different schedules based on content type
        schedules = {}
        
        # Main content posting - spread across optimal hours
        if len(optimal_hours) >= 3:
            main_hours = optimal_hours[:3]
            schedules["content_posting"] = f"0 {','.join(map(str, main_hours))} * * {cron_days_str}"
        else:
            schedules["content_posting"] = f"0 {','.join(map(str, optimal_hours))} * * *"
        
        # Interactive tasks - more frequent during peak hours
        peak_hour = optimal_hours[0] if optimal_hours else 12
        schedules["interactions"] = f"*/15 {peak_hour}-{(peak_hour + 4) % 24} * * *"
        
        # Engagement monitoring - after main posting hours
        monitor_hour = (optimal_hours[-1] + 1) % 24 if optimal_hours else 13
        schedules["engagement_check"] = f"30 {monitor_hour} * * *"
        
        self.logger.info(f"Generated optimal schedules for {platform}: {schedules}")
        
        return schedules
    
    def calculate_post_spacing(self, platform: str, posts_per_day: int) -> List[int]:
        """Calculate optimal spacing between posts throughout the day."""
        optimal_hours = self.analyzer.get_optimal_hours(platform, posts_per_day)
        
        if posts_per_day <= len(optimal_hours):
            return optimal_hours[:posts_per_day]
        
        # If we need more posts than optimal hours, distribute evenly
        spacing_hours = 24 // posts_per_day
        distributed_hours = []
        
        start_hour = optimal_hours[0] if optimal_hours else 9
        
        for i in range(posts_per_day):
            hour = (start_hour + (i * spacing_hours)) % 24
            distributed_hours.append(hour)
        
        return sorted(distributed_hours)
    
    def avoid_platform_conflicts(self, all_schedules: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        """Adjust schedules to avoid posting on multiple platforms simultaneously."""
        optimized_schedules = {}
        
        # Extract all posting times
        posting_times = []
        for platform, schedules in all_schedules.items():
            content_schedule = schedules.get("content_posting", "")
            if content_schedule:
                # Parse cron to get hours (simplified parsing)
                parts = content_schedule.split()
                if len(parts) >= 2:
                    hours_str = parts[1]
                    try:
                        if ',' in hours_str:
                            hours = [int(h) for h in hours_str.split(',')]
                        else:
                            hours = [int(hours_str)]
                        
                        for hour in hours:
                            posting_times.append((platform, hour))
                    except ValueError:
                        continue
        
        # Group conflicts
        conflicts = defaultdict(list)
        for platform, hour in posting_times:
            conflicts[hour].append(platform)
        
        # Resolve conflicts by shifting times
        for platform, schedules in all_schedules.items():
            optimized_schedules[platform] = schedules.copy()
            
            content_schedule = schedules.get("content_posting", "")
            if content_schedule:
                parts = content_schedule.split()
                if len(parts) >= 2:
                    hours_str = parts[1]
                    try:
                        if ',' in hours_str:
                            hours = [int(h) for h in hours_str.split(',')]
                        else:
                            hours = [int(hours_str)]
                        
                        # Adjust conflicting hours
                        adjusted_hours = []
                        for hour in hours:
                            if len(conflicts[hour]) > 1:
                                # Find nearby non-conflicting hour
                                for offset in range(1, 4):
                                    for new_hour in [(hour + offset) % 24, (hour - offset) % 24]:
                                        if len(conflicts[new_hour]) <= 1:
                                            adjusted_hours.append(new_hour)
                                            conflicts[new_hour].append(platform)
                                            break
                                    else:
                                        continue
                                    break
                                else:
                                    adjusted_hours.append(hour)  # Keep original if no alternative
                            else:
                                adjusted_hours.append(hour)
                        
                        # Update schedule with adjusted hours
                        parts[1] = ','.join(map(str, sorted(adjusted_hours)))
                        optimized_schedules[platform]["content_posting"] = ' '.join(parts)
                        
                    except ValueError:
                        pass
        
        self.logger.info("Optimized schedules to avoid platform conflicts")
        return optimized_schedules
    
    def get_engagement_insights(self, platform: str) -> Dict[str, Any]:
        """Get engagement insights and recommendations."""
        if platform not in self.analyzer.engagement_data:
            return {"error": "No engagement data available"}
        
        data = self.analyzer.engagement_data[platform]
        if not data:
            return {"error": "No engagement records found"}
        
        # Calculate insights
        total_records = len(data)
        avg_engagement = statistics.mean([r["engagement_score"] for r in data])
        
        # Best performing posts
        top_posts = sorted(data, key=lambda x: x["engagement_score"], reverse=True)[:5]
        
        # Hour analysis
        hourly_performance = defaultdict(list)
        for record in data:
            hourly_performance[record["hour"]].append(record["engagement_score"])
        
        hourly_avg = {
            hour: statistics.mean(scores) 
            for hour, scores in hourly_performance.items()
        }
        
        best_hour = max(hourly_avg.items(), key=lambda x: x[1]) if hourly_avg else (12, 0)
        worst_hour = min(hourly_avg.items(), key=lambda x: x[1]) if hourly_avg else (3, 0)
        
        # Day analysis
        daily_performance = defaultdict(list)
        for record in data:
            daily_performance[record["day_of_week"]].append(record["engagement_score"])
        
        daily_avg = {
            day: statistics.mean(scores)
            for day, scores in daily_performance.items()
        }
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        best_day = max(daily_avg.items(), key=lambda x: x[1]) if daily_avg else (0, 0)
        worst_day = min(daily_avg.items(), key=lambda x: x[1]) if daily_avg else (0, 0)
        
        return {
            "total_posts": total_records,
            "average_engagement": round(avg_engagement, 2),
            "best_hour": {"hour": best_hour[0], "avg_engagement": round(best_hour[1], 2)},
            "worst_hour": {"hour": worst_hour[0], "avg_engagement": round(worst_hour[1], 2)},
            "best_day": {"day": day_names[best_day[0]], "avg_engagement": round(best_day[1], 2)},
            "worst_day": {"day": day_names[worst_day[0]], "avg_engagement": round(worst_day[1], 2)},
            "top_posts": [
                {
                    "timestamp": post["timestamp"],
                    "engagement_score": post["engagement_score"],
                    "hour": post["hour"]
                }
                for post in top_posts
            ]
        }

def get_timing_optimizer() -> SmartScheduleOptimizer:
    """Get the global timing optimizer instance."""
    if not hasattr(get_timing_optimizer, '_instance'):
        get_timing_optimizer._instance = SmartScheduleOptimizer()
    return get_timing_optimizer._instance