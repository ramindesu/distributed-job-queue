 from django.contrib import admin
 from job.models import Job, JobExecution
 
 
 @admin.register(Job)
 class JobAdmin(admin.ModelAdmin):
     list_display = (
         'id',
         'type',
         'status',
         'worker',
         'retry_count',
         'max_retries',
         'claimed_at',
         'started_at',
         'completed_at',
         'created_at',
     )
     list_filter = ('status', 'type', 'created_at', 'updated_at')
     search_fields = ('id', 'idempotency_key', 'worker__name')
     readonly_fields = ('created_at', 'updated_at', 'claim_expired', 'execution_expired')
     raw_id_fields = ('worker',)
     date_hierarchy = 'created_at'
     ordering = ('-created_at',)
     
     fieldsets = (
         ('Job Information', {
             'fields': ('idempotency_key', 'type', 'payload', 'status')
         }),
         ('Worker Assignment', {
             'fields': ('worker',)
         }),
         ('Retry Configuration', {
             'fields': ('retry_count', 'max_retries')
         }),
         ('Timestamps', {
             'fields': ('claimed_at', 'started_at', 'completed_at', 'created_at', 'updated_at')
         }),
         ('Status Check', {
             'fields': ('claim_expired', 'execution_expired'),
             'classes': ('collapse',)
         }),
     )
 
 
 @admin.register(JobExecution)
 class JobExecutionAdmin(admin.ModelAdmin):
     list_display = (
         'id',
         'job',
         'worker',
         'status',
         'started_at',
         'finished_at',
         'created_at',
     )
     list_filter = ('status', 'started_at', 'finished_at')
     search_fields = ('id', 'job__id', 'worker__name', 'error_message')
     readonly_fields = ('created_at',)
     raw_id_fields = ('job', 'worker')
     date_hierarchy = 'started_at'
     ordering = ('-started_at',)
     
     fieldsets = (
         ('Execution Information', {
             'fields': ('job', 'worker', 'status')
         }),
         ('Timing', {
             'fields': ('started_at', 'finished_at', 'created_at')
         }),
         ('Results', {
             'fields': ('result', 'error_message')
         }),
     )
