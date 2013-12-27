from objectset.resources import get_url_patterns
from .models import RecordSet


urlpatterns = get_url_patterns(RecordSet)
