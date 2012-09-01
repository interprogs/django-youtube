from django.db import models
from django_youtube import api
import django.dispatch
from django.utils.translation import ugettext as _

#
# Models
#

class Video(models.Model):
    user = models.ForeignKey('auth.User')
    video_id = models.CharField(max_length=255, unique=True, help_text=_("The Youtube id of the video"))
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    keywords = models.CharField(max_length=200, null=True, blank=True, help_text=_("Comma seperated keywords"))
    is_private = models.BooleanField(default=False)
    youtube_url = models.URLField(max_length=255, null=True, blank=True)
    swf_url = models.URLField(max_length=255, null=True, blank=True)
    
    def __unicode__(self):
        return self.title
    
    def get_absolute_url(self):
        return self.swf_url
    
    def entry(self):
        """
        Connects to Youtube Api and retrieves the video entry object
        
        Return:
            gdata.youtube.YouTubeVideoEntry
        """
        return api.fetch_video(self.video_id)
    
    def save(self, *args, **kwargs):
        """
        Overrides the default save method
        Connects to API to fetch detailed info about the video
        and stores them in the model
        """
        
        # if this is a new instance add details from api
        if not self.id:
            # Connect to api and get the details
            entry = self.entry()
            
            # Set the details
            self.title = entry.media.title.text
            self.description = entry.media.description.text
            self.keywords = entry.media.keywords.text
            self.youtube_url = entry.media.player.url
            self.swf_url = entry.GetSwfUrl()
            self.is_private = True if entry.media.private else False
        
            # Save the instance
            super(Video, self).save(*args, **kwargs)
            
            # show thumbnails
            for thumbnail in entry.media.thumbnail:
                t = Thumbnail()
                t.url = thumbnail.url
                t.video = self
                t.save()
        else:
            # updating the video instance
            # Connect to API and update video on facebook
            
            # update method needs authentication
            from django.conf import settings
            api.authenticate(settings.YOUTUBE_AUTH_EMAIL, settings.YOUTUBE_AUTH_PASSWORD, settings.YOUTUBE_CLIENT_ID)
            
            # Update the info on youtube
            api.update_video(self.video_id, self.title, self.description, self.keywords)
            
        # Save the model
        return super(Video, self).save(*args, **kwargs)
            
    def delete(self, *args, **kwargs):
        """
        Deletes the video from youtube
        
        Raises:
            OperationError
        """
        
        # Authentication is required for deletion
        from django.conf import settings
        api.authenticate(settings.YOUTUBE_AUTH_EMAIL, settings.YOUTUBE_AUTH_PASSWORD, settings.YOUTUBE_CLIENT_ID)
        
        # Send API request
        deleted = api.delete_video(self.video_id)
        
        # Prevent deletion from db, if api fails
        if not deleted:
            raise api.OperationError(_("Cannot be deleted from Youtube"))
        
        # Call the super method
        return super(Video, self).delete(*args, **kwargs)
    
    def default_thumbnail(self):
        """
        Returns the 1st thumbnail in thumbnails
        This method can be updated as adding default attribute the Thumbnail model and return it
        
        Returns:
            Thumbnail object
        """
        return self.thumbnail_set.all()[0]
    
class Thumbnail(models.Model):
    video = models.ForeignKey(Video, null=True)
    url = models.URLField(max_length=255)
    
    def __unicode__(self):
        return self.url
    
    def get_absolute_url(self):
        return self.url

#
# Signal Definitions
#

video_created = django.dispatch.Signal(providing_args=["video"])