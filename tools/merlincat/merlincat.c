#include <stdio.h>
#include <glib.h>

#include <signal.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>

#include "client_gsource.h"
#include "merlinreader.h"
#include "console.h"
#include "event_packer.h"
#include <shared/shared.h>
#include <shared/compat.h>

GMainLoop *g_mainloop = NULL;
char *program_name;

static void stop_mainloop(int signal);

static gpointer net_send_ctrl_active(gpointer conn);
static gpointer net_conn_new(gpointer conn, gpointer user_data);
static void net_conn_data(gpointer conn, gpointer buffer, gsize length, gpointer conn_user_data);
static void net_conn_close(gpointer conn_user_data);
static void console_newline(const char *line, gpointer user_data);

static void usage(char *msg) __attribute__((noreturn));
static void parse_args(struct ConnectionInfo *conn, int argc, char *argv[]);


int main(int argc, char *argv[]) {
	ClientSource *cs = NULL;

	/* Reference to the current connection, to send data asynchronously */
	gpointer *current_conn = NULL;

	int retcode = 0;

	ConsoleIO *cio;
	program_name = argv[0];

	struct ConnectionInfo conn_info;
	parse_args(&conn_info, argc, argv);

	g_type_init();

	/*
	 * Create main loop, contains information about what should be checked. Is a
	 * singleton
	 */
	g_mainloop = g_main_loop_new(NULL, TRUE);

	/* non glib-unix version of stopping signals */
	signal(SIGHUP, stop_mainloop);
	signal(SIGINT, stop_mainloop);
	signal(SIGTERM, stop_mainloop);

	cs = client_source_new(&conn_info, net_conn_new, net_conn_data, net_conn_close, &current_conn);
	if(cs == NULL) {
		fprintf(stderr, "Could not connect\n");
		retcode = 1;
		goto cleanup;
	}

	cio = consoleio_new(console_newline, (gpointer)&current_conn);

	g_main_loop_run(g_mainloop);

cleanup:
	consoleio_destroy(cio);
	client_source_destroy(cs);
	g_main_loop_unref(g_mainloop);
	return retcode;
}

static void stop_mainloop(int signal) {
	g_main_loop_quit(g_mainloop);
}

static gpointer net_send_ctrl_active(gpointer conn) {
	merlin_event pkt;
	merlin_nodeinfo node;

	memset(&pkt.hdr, 0, HDR_SIZE);
	memset(&node, 0, sizeof(merlin_nodeinfo));

	pkt.hdr.sig.id = MERLIN_SIGNATURE;
	pkt.hdr.protocol = MERLIN_PROTOCOL_VERSION;
	gettimeofday(&pkt.hdr.sent, NULL);
	pkt.hdr.type = CTRL_PACKET;
	pkt.hdr.code = CTRL_ACTIVE;
	pkt.hdr.selection = CTRL_GENERIC & 0xffff;

	node.version = 1; //MERLIN_NODEINFO_VERSION;
	node.word_size = 64; //COMPAT_WORDSIZE;
	node.byte_order = 1234; //endianness();
	node.monitored_object_state_size = sizeof(monitored_object_state);
	node.object_structure_version = 402; //CURRENT_OBJECT_STRUCTURE_VERSION;
	gettimeofday(&node.start, NULL);

	node.last_cfg_change = 1444405566;
	strcpy(node.config_hash, "");//"a77d59a6578c71d7e17f4793a08bcf15d4c6fa06");

	node.configured_peers = 1;

	pkt.hdr.len = sizeof(merlin_nodeinfo);
	memcpy(&pkt.body, &node, sizeof(merlin_nodeinfo));

	client_source_send(conn, &pkt, HDR_SIZE + pkt.hdr.len);
}

static gpointer net_conn_new(gpointer conn, gpointer user_data) {
	gpointer *current_conn = (gpointer*)user_data;
	MerlinReader *mr = merlinreader_new();

	/* Save this socket, so we can send data to it later */
	*current_conn = conn;

	net_send_ctrl_active(*current_conn);

	return mr;
}
static void net_conn_data(gpointer conn, gpointer buffer, gsize length, gpointer conn_user_data) {
	MerlinReader *mr = (MerlinReader *)conn_user_data;
	merlin_event *evt;
	gsize read_size;
	char *buf;
	while(length) {
		read_size = merlinreader_add_data(mr, buffer, length);
		length -= read_size;
		buffer += read_size;

		while(NULL != (evt = merlinreader_get_event(mr))) {
			buf = event_packer_pack(evt);
			printf("%s\n", buf);
			free(buf);
			g_free(evt);
		}
	}
}
static void net_conn_close(gpointer conn_user_data) {
	MerlinReader *mr = (MerlinReader *)conn_user_data;
	merlinreader_destroy(mr);
	g_main_loop_quit(g_mainloop);
}

static void console_newline(const char *line, gpointer user_data) {
	gpointer *current_conn = (gpointer*)user_data;
	merlin_event *evt = NULL;

	if(*current_conn == NULL) {
		fprintf(stderr, "Trying to send while not connected\n");
		return;
	}

	evt = event_packer_unpack(line);
	if(evt == NULL) {
		fprintf(stderr, "Malformed packet from console\n");
		return;
	}
	client_source_send(*current_conn, evt, HDR_SIZE + evt->hdr.len);
	free(evt);
}

static void usage(char *msg) {
	if (msg)
		printf("%s\n\n", msg);

	printf("Usage: %s -t <conntype> -d <address> [-l] [-s <address>]\n", program_name);
	printf("  -t <conntype>   Specify connection type ('unix' or 'inet')\n");
	printf("  -d <address>    Address parameters\n");
	printf("  -s <address>    Source address parameters (optional)\n");
	printf("  -l              Listen instead of connect (default: no)\n");
	printf("\n  An \"address\" consists of <address>:<ip>\n");
	exit(EXIT_FAILURE);
}

static void parse_args(struct ConnectionInfo *conn_info, int argc, char *argv[]) {
	int c;
	char *dest   = NULL;
	char *source = NULL;
	opterr = 0;

	/* Initial values for conn_info */
	memset(conn_info, 0, sizeof(*conn_info));
	conn_info->type = -1;

	while((c = getopt(argc, argv, "t:d:s:l:")) != -1) {
		switch(c) {
			case 't':
				/* Connection type. Could be tcp, unix, etc... */
				if (0 == strcasecmp("inet", optarg))
					conn_info->type = AF_INET;
				else if (0 == strcasecmp("unix", optarg))
					conn_info->type = AF_UNIX;
				else
					usage("Invalid argument for option -t");
				break;
			case 'd':
				/*
				 * Connection destination. Format depending on type.
				 * Save destination and parse later when we know the type.
				 */
				dest = strdup(optarg);
				break;
			case 's':
				/*
				 * Connection source. Only applicable on some types.
				 * Save source and parse later when we know the type.
				 */
				source = strdup(optarg);
				break;
			case 'l':
				/* TODO: Implement this when it is needed for testing. */
				break;
			case '?':
			default:
				usage("Option not found or missing argument for option");
		}
	}

	if (conn_info->type == -1 || dest == NULL) {
		usage("Required option(s) missing");
	}

	if (optind != argc) {
		int i;
		printf("Unhandled arguments present: ");
		for (i = optind; i < argc; i++) {
			printf("%s%s", argv[i], i == argc - 1 ? "\n" : ", ");
		}
		usage(NULL);
	}

	switch (conn_info->type) {
		case AF_UNIX:
			/* TODO: Check that destination seems to be correct. Ignore source. */

			break;
		case AF_INET:
			/* Parse address and port from dest string. */
			conn_info->dest_addr = strsep(&dest, ":"); /* Moves pointer in dest to dest_addr. */
			if (dest)
				conn_info->dest_port = atoi(dest);
			else
				usage("Destination port required");
			dest = NULL;

			/* Parse address and port from source string. */
			if (source) {
				conn_info->source_addr = strsep(&source, ":"); /* Moves pointer in source to source_addr. */
				if (source)
					conn_info->source_port = atoi(source);
				source = NULL;
			}
			break;
		default:
			/* We can never end up here */
			break;
	}

	if (dest)   free(dest);
	if (source) free(source);
}