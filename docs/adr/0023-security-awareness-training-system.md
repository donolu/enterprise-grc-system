# ADR 0023: Security Awareness Training System

## Status
Accepted and Implemented ✅

## Context
The organization needed a comprehensive security awareness training platform that allows administrators to schedule recurring email campaigns with awareness content and provides a video training library with support for external providers like Synthesia.io. This system must integrate seamlessly with the existing GRC platform and provide analytics on training effectiveness.

## Decision
We implemented a full-featured security awareness training system with the following key architectural decisions:

### 1. Dual Training Delivery System
- **Email Campaigns**: Scheduled awareness content delivery via automated email campaigns
- **Video Library**: On-demand video training with multi-provider support
- **Integrated Analytics**: Comprehensive tracking across both delivery methods

### 2. Multi-Provider Video Integration
- **Synthesia.io**: Primary AI-generated video provider with embed support
- **YouTube**: Popular video hosting with iframe embedding
- **Vimeo**: Professional video hosting with privacy controls
- **Custom URLs**: Flexibility for other video providers or self-hosted content

### 3. Campaign Automation System
- **Flexible Scheduling**: Weekly, bi-weekly, monthly, and quarterly campaigns
- **Smart Targeting**: Send to all users or specific user groups
- **Template Processing**: Dynamic content with user personalization
- **Delivery Tracking**: Complete email delivery and engagement analytics

### 4. Advanced Analytics Framework
- **Video Metrics**: View counts, completion rates, engagement time
- **Campaign Metrics**: Open rates, click rates, delivery success
- **User Progress**: Individual and aggregate training progress
- **Automated Reporting**: Weekly analytics reports with actionable insights

## Implementation Architecture

### Models (`training/models.py`)
```python
# Core training content organization
TrainingCategory  # Organizational categories with color coding
TrainingVideo     # Multi-provider video content with analytics

# Email campaign system
SecurityAwarenessCampaign  # Scheduled email campaigns
CampaignDelivery          # Individual delivery tracking

# Analytics and tracking
VideoView  # Video viewing sessions with completion tracking
```

### Campaign Automation (`training/tasks.py`)
- **Hourly Campaign Delivery**: `send_scheduled_awareness_campaigns`
- **Campaign Execution**: `send_awareness_campaign` with user targeting
- **Analytics Generation**: `generate_training_analytics_report`
- **Data Maintenance**: `cleanup_old_campaign_deliveries`

### Video Integration
```python
@property
def embed_url(self):
    """Generate embed URL based on provider."""
    if self.video_provider == 'synthesia':
        return self.video_url  # Direct Synthesia embed
    elif self.video_provider == 'youtube':
        return f"https://www.youtube.com/embed/{self.video_id}"
    elif self.video_provider == 'vimeo':
        return f"https://player.vimeo.com/video/{self.video_id}"
    # Additional provider support...
```

### API Architecture (`training/views.py`, `training/serializers.py`)
- **5 ViewSets**: Complete CRUD operations with custom actions
- **11 Serializers**: Optimized for different use cases and analytics
- **Advanced Filtering**: 15+ filter options across all training entities
- **Real-time Tracking**: Video view tracking with completion analytics

## Key Features Delivered

### 1. Email Campaign Management
- **Visual Campaign Builder**: Rich admin interface for campaign creation
- **Smart Scheduling**: Automated delivery based on frequency settings
- **Template Engine**: Dynamic content with user personalization variables
- **Engagement Tracking**: Open rates, click rates, and delivery analytics

### 2. Video Training Library
- **Multi-Provider Support**: Synthesia.io, YouTube, Vimeo, and custom URLs
- **Category Organization**: Color-coded categories with filtering
- **Difficulty Levels**: Beginner, intermediate, and advanced content
- **Progress Tracking**: Individual viewing progress and completion status

### 3. Professional Admin Interface
- **Campaign Management**: Visual campaign status with color coding
- **Video Library**: Bulk operations for publishing and categorization
- **Analytics Dashboard**: Real-time metrics and engagement statistics
- **Bulk Operations**: Publish/unpublish videos, activate/deactivate campaigns

### 4. Frontend User Experience
- **Video Library**: Responsive grid with search and filtering
- **Video Player**: Dedicated player pages with progress tracking
- **Completion Tracking**: Visual progress indicators and completion badges
- **Mobile Responsive**: Optimized for all device sizes

## API Endpoints
```
/api/training/categories/                    # Training categories
/api/training/videos/                        # Video library
/api/training/videos/{id}/track_view/        # View tracking
/api/training/campaigns/                     # Email campaigns
/api/training/campaigns/{id}/send_now/       # Manual campaign trigger
/api/training/campaigns/{id}/test_send/      # Test email delivery
/api/training/deliveries/                    # Delivery tracking
/api/training/views/                         # Video analytics
/api/training/dashboard/                     # Analytics dashboard
```

## Celery Task Schedule
```python
# Hourly campaign delivery
'send-scheduled-awareness-campaigns': crontab(minute=0)

# Weekly analytics report (Saturday 6 PM)
'generate-training-analytics-report': crontab(day_of_week=6, hour=18)

# Data cleanup (Sunday 1 AM)
'cleanup-old-campaign-deliveries': crontab(day_of_week=0, hour=1)

# View count synchronization (Daily 2 AM)
'update-video-view-counts': crontab(hour=2, minute=0)
```

## Integration Points
- **Multi-tenant Architecture**: Full tenant isolation using django-tenants
- **Email Infrastructure**: Leverages existing Django email configuration
- **User Management**: Integration with existing User model and permissions
- **Celery Infrastructure**: Uses existing Redis/Celery setup for task processing
- **Admin Styling**: Consistent with existing admin interface patterns

## Synthesia.io Integration
- **Direct Embed Support**: Iframe embedding of Synthesia-generated videos
- **Flexible URL Handling**: Support for various Synthesia URL formats
- **Analytics Tracking**: View completion and engagement metrics
- **Responsive Design**: Mobile-optimized video player interface

## Analytics and Reporting
- **Video Analytics**: View counts, completion rates, popular content
- **Campaign Analytics**: Delivery rates, engagement metrics, user targeting
- **Weekly Reports**: Automated analytics emails with actionable insights
- **Real-time Dashboard**: Live metrics and performance indicators

## Benefits
1. **Automated Training Delivery**: Reduces manual effort with scheduled campaigns
2. **Multi-Channel Approach**: Combines proactive emails with on-demand videos
3. **Comprehensive Analytics**: Data-driven insights into training effectiveness
4. **Professional Experience**: Modern UI with responsive design and progress tracking
5. **Scalable Architecture**: Handles enterprise-scale training programs
6. **Flexible Content**: Support for multiple video providers and custom content

## Future Enhancements
- **Interactive Assessments**: Quizzes and knowledge checks
- **Learning Paths**: Structured training sequences
- **Certificates**: Training completion certificates
- **Social Features**: User comments and ratings
- **Advanced Analytics**: Machine learning insights and recommendations

## Date
2024-08-24

## Authors
Development Team