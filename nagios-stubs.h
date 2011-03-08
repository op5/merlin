/* variables provided by Nagios and required by module */
#include "nagios/macros.h"
char *config_file = "/opt/monitor/etc/nagios.cfg";
service *service_list = NULL;
hostgroup *hostgroup_list = NULL;
host *host_list = NULL;
#define macro_x global_macros.x
int event_broker_options = 0;
int daemon_dumps_core = 0;
sched_info scheduling_info;
#define num_hosts scheduling_info.total_hosts
#define num_services scheduling_info.total_services
int __nagios_object_structure_version = CURRENT_OBJECT_STRUCTURE_VERSION;

static nagios_macros global_macros;
int add_new_comment(int comment_type, int entry_type, char *host_name, time_t entry_time, char *author_name, char *comment_data, int persistent, int source, int expires, time_t expire_time, unsigned long *comment_id)
{
	return 0;
}
nagios_macros *get_global_macros(void)
{
	return &global_macros;
}

/* nagios functions we must have for dlopen() to work properly */
int schedule_new_event(int a, int b, time_t c, int d, unsigned long e,
					   void *f, int g, void *h, void *i, int j)
{
	return 0;
}
host *find_host(char *host_name)
{
	return NULL;
}
service *find_service(char *host_name, char *service_description)
{
	return NULL;
}
int update_all_status_data(void)
{
	return 0;
}
int process_external_command2(int cmd_id, time_t entry_time, char *args)
{
	return 0;
}
int update_host_performance_data(host *hst)
{
	return 0;
}
int update_service_performance_data(host *hst)
{
	return 0;
}
void xodtemplate_grab_config_info(void)
{
	macro_x[MACRO_OBJECTCACHEFILE] = "/opt/monitor/etc/nagios.cfg";
}
