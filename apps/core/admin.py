from django.contrib import admin

from apps.core.models import (
    Answer,
    Question,
    QuestionOption,
    RespondentProfile,
    Response,
    SentimentAnalysisResult,
    Survey,
    TargetingCriteria,
    User,
)


admin.site.register(User)
admin.site.register(RespondentProfile)
admin.site.register(Survey)
admin.site.register(Question)
admin.site.register(QuestionOption)
admin.site.register(TargetingCriteria)
admin.site.register(Response)
admin.site.register(Answer)
admin.site.register(SentimentAnalysisResult)
