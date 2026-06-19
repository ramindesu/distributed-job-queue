 from django.contrib import admin
 from worker.models import Worker
 
 
 @admin.register(Worker)
 class WorkerAdmin(admin.ModelAdmin):
     list_display = (
         'id',
         'name',
         'status',
         'last_heartbeat',
         'is_alive',
         'created_at',
         'updated_at',
     )
     list_filter = ('status', 'created_at', 'last_heartbeat')
     search_fields = ('name',)
     readonly_fields = ('created_at', 'updated_at', 'is_alive')
     date_hierarchy = 'created_at'
     ordering = ('-created_at',)
     
     fieldsets = (
         ('Worker Information', {
             'fields': ('name', 'status')
         }),
         ('Health Check', {
             'fields': ('last_heartbeat', 'is_alive')
         }),
         ('Timestamps', {
             'fields': ('created_at', 'updated_at')
         }),
     )
