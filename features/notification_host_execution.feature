@config @daemons @merlin @queryhandler @livestatus
Feature: Notification execution for host notificaitons
	Notification scripts should only be executed on one node; the node that
	identifies the notification.

	In a peered environment, it should be the peer that is responsible for
	executing the script.

	In a poller environment, it is the node peered poller that is responsible
	for executing the plugin, if the pollers is configured in for notification.
	Otherwise, it is the master to the peer that has responsibility for the
	service/host given that the pollers wouldn't be there.

	In any case, the merlin packets for notifications is just informative, that
	should only be treated as information for logging to database. The only
	packets that can affect nofification commands to be executed is the packets
	regarding check results, which triggers the check result handling of naemon
	itself.

	Background: Set up naemon configuration
		Given I have naemon hostgroup objects
			| hostgroup_name | alias |
			| pollergroup    | PG    |
			| emptygroup     | EG    |
		And I have naemon host objects
			| use          | host_name | address   | contacts  | max_check_attempts | hostgroups  |
			| default-host | hostA     | 127.0.0.1 | myContact | 2                  | pollergroup |
			| default-host | hostB     | 127.0.0.2 | myContact | 2                  | pollergroup |
		And I have naemon service objects
			| use             | host_name | description |
			| default-service | hostA     | PONG        |
			| default-service | hostB     | PONG        |
		And I have naemon contact objects
			| use             | contact_name |
			| default-contact | myContact    |

	Scenario: One master notifies if poller doesn't notify, given merlin HOST_CHECK events is received
		This node should notify for hostB
		Given I start naemon with merlin nodes connected
			| type   | name       | port | hostgroup   | notifies |
			| poller | the_poller | 4001 | pollergroup | no       |
			| peer   | the_peer   | 4002 | ignore      | ignore   |

		And the_poller sends event HOST_CHECK
			| name                     | hostB    |
			| state.state_type         | 0        |
			| state.current_state      | 1        |
			| state.current_attempt    | 1        |
			| state.plugin_output      | 1st line |
			| state.long_plugin_output | 2nd line |
		And the_poller sends event HOST_CHECK
			| name                     | hostB    |
			| state.state_type         | 1        |
			| state.current_state      | 1        |
			| state.current_attempt    | 2        |
			| state.plugin_output      | 1st line |
			| state.long_plugin_output | 2nd line |
		And I wait for 1 second

		Then 1 host notification was sent
			| parameter        | value    |
			| hostname         | hostB    |
			| hoststate        | DOWN     |
			| notificationtype | PROBLEM  |
			| hostoutput       | 1st line |
			| longhostoutput   | 2nd line |

	Scenario: One master notifies if poller doesn't notify, given merlin HOST_CHECK events is received
		A peer should notify for hostA, so this should not notify
		Given I start naemon with merlin nodes connected
			| type   | name       | port | hostgroup   | notifies |
			| poller | the_poller | 4001 | pollergroup | no       |
			| peer   | the_peer   | 4002 | ignore      | ignore   |

		And the_poller sends event HOST_CHECK
			| name                     | hostA    |
			| state.state_type         | 0        |
			| state.current_state      | 1        |
			| state.current_attempt    | 1        |
			| state.plugin_output      | 1st line |
			| state.long_plugin_output | 2nd line |
		And the_poller sends event HOST_CHECK
			| name                     | hostA    |
			| state.state_type         | 1        |
			| state.current_state      | 1        |
			| state.current_attempt    | 2        |
			| state.plugin_output      | 1st line |
			| state.long_plugin_output | 2nd line |
		And I wait for 1 second

		Then no host notification was sent

	Scenario: No masters notifies if poller notifies, given merlin HOST_CHECK events is received
		Given I start naemon with merlin nodes connected
			| type   | name       | port | hostgroup   | notifies |
			| poller | the_poller | 4001 | pollergroup | yes      |
			| peer   | the_peer   | 4002 | ignore      | ignore   |

		When the_poller sends event HOST_CHECK
			| name                  | hostA |
			| state.state_type      | 0     |
			| state.current_state   | 1     |
			| state.current_attempt | 1     |
		And the_poller sends event HOST_CHECK
			| name                  | hostB |
			| state.state_type      | 0     |
			| state.current_state   | 1     |
			| state.current_attempt | 1     |
		And the_poller sends event HOST_CHECK
			| name                  | hostA |
			| state.state_type      | 1     |
			| state.current_state   | 1     |
			| state.current_attempt | 2     |
		And the_poller sends event HOST_CHECK
			| name                  | hostB |
			| state.state_type      | 1     |
			| state.current_state   | 1     |
			| state.current_attempt | 2     |
		And I wait for 1 second

		Then no host notification was sent

	Scenario: Poller should notify if poller is configured to notify
		Given I start naemon with merlin nodes connected
			| type   | name       | port |
			| master | my_master  | 4001 |

		When I send naemon command PROCESS_HOST_CHECK_RESULT;hostA;0;First OK
		# Passive checks goes hard directly
		And I send naemon command PROCESS_HOST_CHECK_RESULT;hostA;1;Not OK
		And I wait for 1 second

		Then 1 host notification was sent
			| parameter        | value   |
			| hostname         | hostA   |
			| hoststate        | DOWN    |
			| notificationtype | PROBLEM |
			| hostoutput       | Not OK  |
		And my_master received event CONTACT_NOTIFICATION_METHOD
			| host_name    | hostA     |
			| contact_name | myContact |

	Scenario: Passive check result should only be executed on machine handling the check, when getting from QH/command pipe
		Given I start naemon with merlin nodes connected
			| type   | name        | port | hostgroup  |
			| peer   | the_peer    | 4001 | ignore     |
			| poller | the_poller  | 4002 | emptygroup |

		When I send naemon command PROCESS_HOST_CHECK_RESULT;hostA;0;First OK
		And I send naemon command PROCESS_HOST_CHECK_RESULT;hostB;0;First OK
		# Passive checks goes hard directly
		And I send naemon command PROCESS_HOST_CHECK_RESULT;hostA;1;Not OK
		And I send naemon command PROCESS_HOST_CHECK_RESULT;hostB;1;Not OK

		Then the_peer received event EXTERNAL_COMMAND
			| command_type   | 87                        |
			| command_string | PROCESS_HOST_CHECK_RESULT |
			| command_args   | hostA;0;First OK          |
		And the_peer received event EXTERNAL_COMMAND
			| command_type   | 87                        |
			| command_string | PROCESS_HOST_CHECK_RESULT |
			| command_args   | hostB;0;First OK          |
		And the_peer received event EXTERNAL_COMMAND
			| command_type   | 87                        |
			| command_string | PROCESS_HOST_CHECK_RESULT |
			| command_args   | hostA;1;Not OK            |
		And the_peer received event EXTERNAL_COMMAND
			| command_type   | 87                        |
			| command_string | PROCESS_HOST_CHECK_RESULT |
			| command_args   | hostB;1;Not OK            |
		And the_poller should not receive EXTERNAL_COMMAND
		And 1 host notification was sent
			| parameter        | value   |
			| hostname         | hostB   |
			| hoststate        | DOWN    |
			| notificationtype | PROBLEM |
			| hostoutput       | Not OK  |

	Scenario: Passive check result should only be executed on machine handling the check, when getting from merlin
		Given I start naemon with merlin nodes connected
			| type   | name        | port | hostgroup  |
			| peer   | the_peer    | 4001 | ignore     |
			| poller | the_poller  | 4002 | emptygroup |

		When the_peer sends event EXTERNAL_COMMAND
			| command_type   | 87                        |
			| command_string | PROCESS_HOST_CHECK_RESULT |
			| command_args   | hostA;0;First OK          |
		And the_peer sends event EXTERNAL_COMMAND
			| command_type   | 87                        |
			| command_string | PROCESS_HOST_CHECK_RESULT |
			| command_args   | hostB;0;First OK          |
		And the_peer sends event EXTERNAL_COMMAND
			| command_type   | 87                        |
			| command_string | PROCESS_HOST_CHECK_RESULT |
			| command_args   | hostA;1;Not OK            |
		And the_peer sends event EXTERNAL_COMMAND
			| command_type   | 87                        |
			| command_string | PROCESS_HOST_CHECK_RESULT |
			| command_args   | hostB;1;Not OK            |

		# Next line waits
		Then the_peer should not receive EXTERNAL_COMMAND
		And the_poller should not receive EXTERNAL_COMMAND
		And 1 host notification was sent
			| parameter        | value   |
			| hostname         | hostB   |
			| hoststate        | DOWN    |
			| notificationtype | PROBLEM |
			| hostoutput       | Not OK  |
		
	Scenario: Passive checks should be executed on poller if poller handling the check
		Given I start naemon with merlin nodes connected
			| type   | name       | port | hostgroup   |
			| poller | the_poller | 4001 | pollergroup |
			
		When I send naemon command PROCESS_HOST_CHECK_RESULT;hostA;0;First OK
		# Passive checks goes hard directly
		And I send naemon command PROCESS_HOST_CHECK_RESULT;hostA;1;Not OK
		And I wait for 1 second

		Then the_poller received event EXTERNAL_COMMAND
			| command_type   | 87                        |
			| command_string | PROCESS_HOST_CHECK_RESULT |
			| command_args   | hostA;0;First OK          |
		And the_poller received event EXTERNAL_COMMAND
			| command_type   | 87                        |
			| command_string | PROCESS_HOST_CHECK_RESULT |
			| command_args   | hostA;1;Not OK            |
		And no host notification was sent
		
	Scenario: Passive checks sent from master handled by correct node in pollergroup
		Given I start naemon with merlin nodes connected
			| type   | name         | port |
			| master | the_master   | 4001 |
			| peer   | other_poller | 4002 |

		When the_master sends event EXTERNAL_COMMAND
			| command_type   | 87                        |
			| command_string | PROCESS_HOST_CHECK_RESULT |
			| command_args   | hostA;0;First OK          |
		And the_master sends event EXTERNAL_COMMAND
			| command_type   | 87                        |
			| command_string | PROCESS_HOST_CHECK_RESULT |
			| command_args   | hostB;0;First OK          |
		And the_master sends event EXTERNAL_COMMAND
			| command_type   | 87                        |
			| command_string | PROCESS_HOST_CHECK_RESULT |
			| command_args   | hostA;1;Not OK            |
		And the_master sends event EXTERNAL_COMMAND
			| command_type   | 87                        |
			| command_string | PROCESS_HOST_CHECK_RESULT |
			| command_args   | hostB;1;Not OK            |

		Then the_master should not receive EXTERNAL_COMMAND
		And other_poller should not receive EXTERNAL_COMMAND
		And 1 host notification was sent
			| parameter        | value   |
			| hostname         | hostB   |
			| hoststate        | DOWN    |
			| notificationtype | PROBLEM |
			| hostoutput       | Not OK  |

	Scenario: As a poller with notifications turned off, notification
		should be handled by a master.

		Given I have merlin config notifies set to no
		And I start naemon with merlin nodes connected
			| type   | name         | port |
			| master | the_master   | 4001 |

		When I send naemon command PROCESS_HOST_CHECK_RESULT;hostA;0;First OK
		# Passive checks goes hard directly
		And I send naemon command PROCESS_HOST_CHECK_RESULT;hostA;1;Not OK

		Then no host notification was sent

    Scenario: Notification should be sent for an owned object if the object
        was previously owned by another peer.
        Given I start naemon with merlin nodes connected
            | type   | name         | port | hostgroup  | notifies |
            | peer   | peer_one     | 4001 | ignore     | ignore   |
            | peer   | peer_two     | 4002 | ignore     | ignore   |
        And peer_one becomes disconnected
        
        When peer_two sends event EXTERNAL_COMMAND
            | command_type   | 87                        |
            | command_string | PROCESS_HOST_CHECK_RESULT |
            | command_args   | hostB;1;MON-10202         |
            
        Then plugin_output of host hostB should be MON-10202
        And file naemon.log does not match Notification will be handled by owning peer
        And 1 host notification was sent
            | parameter        | value     |
            | hostname         | hostB     |
            | notificationtype | PROBLEM   |
            | hoststate        | DOWN      |
            | hostoutput       | MON-10202 |

    Scenario: If a master has configured takeover = yes, then it should notify
        for a host in place of a poller, in case the poller goes down

        Given I have merlin config takeover set to yes
        And I start naemon with merlin nodes connected
            | type   | name       | port | hostgroup   |
            | poller | the_poller | 4001 | pollergroup |

        When the_poller becomes disconnected
        And I send naemon command PROCESS_HOST_CHECK_RESULT;hostA;1;Not OK
        And I send naemon command PROCESS_HOST_CHECK_RESULT;hostB;1;Not OK

        Then 1 host notification was sent
            | parameter        | value  |
            | hostname         | hostA  |
        And 1 host notification was sent
            | parameter        | value  |
            | hostname         | hostB  |

    Scenario: A peer should send custom notification for an object
        it is responsible for, even if the custom notification command is sent
        to the remote naemon daemon

        Given I start naemon with merlin nodes connected
            | type   | name         | port |
            | peer   | the_peer     | 4001 |

        When the_peer sends event EXTERNAL_COMMAND
            | command_type   | 159                           |
            | command_string | SEND_CUSTOM_HOST_NOTIFICATION |
            | command_args   | hostB;0;tester;Comment        |

        Then 1 host notification was sent
            | parameter        | value  |
            | hostname         | hostB  |
            | notificationtype | CUSTOM |

    Scenario: A peer should not send a custom notification for an object
        it is not responsible for, even if it received the command from a peer

        Given I start naemon with merlin nodes connected
            | type   | name         | port |
            | peer   | the_peer     | 4001 |

        When the_peer sends event EXTERNAL_COMMAND
            | command_type   | 159                           |
            | command_string | SEND_CUSTOM_HOST_NOTIFICATION |
            | command_args   | hostA;0;tester;Comment        |

        Then no host notification was sent

    Scenario: A peer should send custom notification for an object it is
        responsible for if the custom notification command is sent to the
        local naemon daemon

        Given I start naemon with merlin nodes connected
            | type   | name         | port |
            | peer   | the_peer     | 4001 |

        When I send naemon command SEND_CUSTOM_HOST_NOTIFICATION;hostB;0;tester;Comment

        Then 1 host notification was sent
            | parameter        | value  |
            | hostname         | hostB  |
            | notificationtype | CUSTOM |

    Scenario: A peer should not send custom notification for an
        object it is not responsible for, even if the custom notification
        command is sent to the local naemon daemon

        Given I start naemon with merlin nodes connected
            | type   | name         | port |
            | peer   | the_peer     | 4001 |

        When I send naemon command SEND_CUSTOM_HOST_NOTIFICATION;hostA;0;tester;Comment

        Then no host notification was sent
