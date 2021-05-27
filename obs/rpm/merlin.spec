%define mod_path /etc/merlin

# function service_control_function ("action", "service")
# start/stop/restart a service
%define create_service_control_function function service_control_function () { service $2 $1; };
%define init_scripts --with-initdirectory=%_sysconfdir/init.d --with-initscripts=data/merlind
%if 0%{?suse_version}
%define mysqld mysql
%define daemon_user naemon
%define daemon_group naemon
%endif
%if 0%{?rhel} == 6
%define mysqld mysqld
%define daemon_user naemon
%define daemon_group naemon
%endif
%if 0%{?rhel} >= 7
%define mysqld mariadb
%define daemon_user naemon
%define daemon_group naemon
%define init_scripts %{nil}
# re-define service_control_function to use systemctl
%define create_service_control_function function service_control_function () { systemctl $1 $2; };
%endif
%define operator_group mon_operators
%define naemon_confdir %_sysconfdir/naemon/

Summary: The merlin daemon is a multiplexing event-transport program
Name: merlin
Version: 2021.4
Release: 0
License: GPLv2
URL: https://github.com/ITRS-Group/monitor-merlin/
Source0: merlin-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}
Requires: libaio
Requires: merlin-apps >= %version
Requires: mariadb
Requires: glib2
Requires: nrpe
Requires: libdbi
Requires: libdbi-dbd-mysql
Requires: libsodium
BuildRequires: libsodium-devel
%if 0%{?rhel} >= 7
BuildRequires: systemd
BuildRequires: mariadb-devel
Obsoletes: merlin-slim
%else
BuildRequires: mysql-devel
%endif
BuildRequires: naemon-devel
BuildRequires: python2
BuildRequires: gperf
BuildRequires: check-devel
BuildRequires: autoconf, automake, libtool
BuildRequires: glib2-devel
BuildRequires: libdbi-devel
BuildRequires: pkgconfig
BuildRequires: pkgconfig(gio-unix-2.0)

%description
The merlin daemon is a multiplexing event-transport program designed to
link multiple Nagios instances together. It can also inject status
data into a variety of databases, using libdbi.

%if 0%{?rhel} >= 7
%package slim
Summary: Slim version of the merlin daemon
Requires: libaio
Requires: merlin-apps-slim >= %version
Requires: glib2
BuildRequires: naemon-devel
BuildRequires: python2
BuildRequires: gperf
BuildRequires: check-devel
BuildRequires: autoconf, automake, libtool
BuildRequires: glib2-devel
BuildRequires: libdbi-devel
BuildRequires: pkgconfig
BuildRequires: pkgconfig(gio-unix-2.0)

%description slim
The merlin daemon is a multiplexing event-transport program designed to
link multiple Nagios instances together. It can also inject status
data into a variety of databases, using libdbi. This version of the package is
slim version that installs fewer dependencies.
%endif

%package -n monitor-merlin
Summary: A Nagios module designed to communicate with the Merlin daemon
Requires: naemon-core, merlin = %version-%release
Requires: mariadb
Obsoletes: monitor-merlin-slim

%description -n monitor-merlin
monitor-merlin is an event broker module running inside Nagios. Its
only purpose in life is to send events from the Nagios core to the
merlin daemon, which then takes appropriate action.

%if 0%{?rhel} >= 7
%package -n monitor-merlin-slim
Summary: A Nagios module designed to communicate with the Merlin daemon
Requires: naemon-slim, merlin-slim = %version-%release

%description -n monitor-merlin-slim
monitor-merlin is an event broker module running inside Nagios. Its
only purpose in life is to send events from the Nagios core to the
merlin daemon, which then takes appropriate action.
%endif

%package apps
Summary: Applications used to set up and aid a merlin/ninja installation
Requires: rsync
Requires: mariadb
%if 0%{?suse_version}
Requires: libdbi1
Requires: python-mysql
%else
%if 0%{?rhel} >= 8
BuildRequires: python2-PyMySQL
%else
Requires: MySQL-python
%endif
Requires: libdbi
%endif
Obsoletes: merlin-apps-slim

%description apps
This package contains standalone applications required by Ninja and
Merlin in order to make them both fully support everything that a
fully fledged op5 Monitor install is supposed to handle.
'mon' works as a single entry point wrapper and general purpose helper
tool for those applications and a wide variety of other different
tasks, such as showing monitor's configuration files, calculating
sha1 checksums and the latest changed such file, as well as
preparing object configuration for pollers, helping with ssh key
management and allround tasks regarding administering a distributed
network monitoring setup.


%if 0%{?rhel} >= 7
%package apps-slim
Summary: Applications used to set up and aid a merlin/ninja installation
Requires: rsync
Requires: openssh
Requires: openssh-clients

%description apps-slim
This package contains standalone applications required by Ninja and
Merlin in order to make them both fully support everything that a
fully fledged op5 Monitor install is supposed to handle.
'mon' works as a single entry point wrapper and general purpose helper
tool for those applications and a wide variety of other different
tasks, such as showing monitor's configuration files, calculating
sha1 checksums and the latest changed such file, as well as
preparing object configuration for pollers, helping with ssh key
management and allround tasks regarding administering a distributed
network monitoring setup.
%endif

%package test
Summary: Test files for merlin
Requires: naemon-livestatus
Requires: naemon-core
Requires: merlin merlin-apps monitor-merlin
# TODO: Fix dependency
#Requires: monitor-testthis
Requires: abrt-cli
Requires: libyaml
Requires: mariadb-devel
Requires: ruby-devel
Requires: python2-nose
# Required development tools for building gems
Requires: make automake gcc
Requires: redhat-rpm-config
BuildRequires: diffutils

%description test
Some additional test files for merlin

%prep
%setup -q

%build
echo %{version} > .version_number
autoreconf -i -s
%configure --disable-auto-postinstall --with-pkgconfdir=%mod_path --with-naemon-config-dir=%naemon_confdir/module-conf.d --with-naemon-user=daemon_user --with-naemon-group=%daemon_user --with-logdir=%{_localstatedir}/log/merlin %init_scripts

%__make V=1
%__make V=1 check

%install
%make_install naemon_user=$(id -un) naemon_group=$(id -gn)

ln -s ../../../../usr/bin/merlind %buildroot/%mod_path/merlind
ln -s ../../../../%_libdir/merlin/import %buildroot/%mod_path/import
ln -s ../../../../%_libdir/merlin/rename %buildroot/%mod_path/rename
ln -s ../../../../%_libdir/merlin/showlog %buildroot/%mod_path/showlog
ln -s ../../../../%_libdir/merlin/merlin.so %buildroot/%mod_path/merlin.so
ln -s op5 %buildroot/%_bindir/mon

cp cukemerlin %buildroot/%_bindir/cukemerlin
cp -r apps/tests %buildroot/usr/share/merlin/app-tests


mkdir -p %buildroot%_sysconfdir/nrpe.d
cp nrpe-merlin.cfg %buildroot%_sysconfdir/nrpe.d

# TODO: Check if systemd
%{__install} -D -m 644 merlind.service %{buildroot}%{_unitdir}/merlind.service

%check
python2 tests/pyunit/test_log.py --verbose
python2 tests/pyunit/test_oconf.py --verbose


%post
%create_service_control_function
# we must stop the merlin deamon so it doesn't interfere with any
# database upgrades, logfile imports and whatnot
service_control_function stop merlind > /dev/null || :

# Verify that mysql-server is installed and running before executing sql scripts
# TODO: fix for non-rhel
%if 0%{?rhel} >= 7
systemctl is-active %mysqld 2&>1 >/dev/null
%else
service %mysqld status 2&>1 >/dev/null
%endif

if [ $? -gt 0 ]; then
  echo "Attempting to start %mysqld..."
  service_control_function start %mysqld
  if [ $? -gt 0 ]; then
    echo "Abort: Failed to start %mysqld."
    exit 1
  fi
fi

if ! mysql -umerlin -pmerlin merlin -e 'show tables' > /dev/null 2>&1; then
    mysql -uroot -e "CREATE DATABASE IF NOT EXISTS merlin"
    mysql -uroot -e "GRANT ALL ON merlin.* TO merlin@localhost IDENTIFIED BY 'merlin'"
fi
%_libdir/merlin/install-merlin.sh

#TODO: check for systemd instead
%if 0%{?rhel} >= 7
systemctl daemon-reload
systemctl enable merlind.service
%else
/sbin/chkconfig --add merlind || :
%endif

# If mysql-server is running _or_ this is an upgrade
# we import logs
if [ $1 -eq 2 ]; then
  mon log import --incremental || :
  mon log import --only-notifications --incremental || :
fi

sed --follow-symlinks -i \
    -e 's#pidfile =.*$#pidfile = /var/run/merlin/merlin.pid;#' \
    -e 's#log_file =.*neb\.log;$#log_file = %{_localstatedir}/log/merlin/neb.log;#' \
    -e 's#log_file =.*daemon\.log;$#log_file = %{_localstatedir}/log/merlin/daemon.log;#' \
    -e 's#ipc_socket =.*$#ipc_socket = /var/lib/merlin/ipc.sock;#' \
    %mod_path/merlin.conf

# chown old cached nodesplit data, so it can be deleted
chown -R %daemon_user:%daemon_group %_localstatedir/cache/merlin

# restart all daemons
for daemon in merlind nrpe; do
    service_control_function restart $daemon
done

# Create operator group for use in sudoers
getent group %operator_group > /dev/null || groupadd %operator_group

%preun -n monitor-merlin
%create_service_control_function
if [ $1 -eq 0 ]; then
    service_control_function stop merlind || :
fi

%postun -n monitor-merlin
%create_service_control_function
if [ $1 -eq 0 ]; then
    service_control_function restart monitor || :
    service_control_function restart nrpe || :
fi

%post -n monitor-merlin
%create_service_control_function
sed --follow-symlinks -i '/broker_module.*merlin.so.*/d' /opt/monitor/etc/naemon.cfg
service_control_function restart naemon || :
service_control_function restart nrpe || :

%files
%defattr(-,root,root)
%dir %attr(750, %daemon_user, %daemon_group) %mod_path
%attr(660, -, %daemon_group) %config(noreplace) %mod_path/merlin.conf
%_datadir/merlin/sql
%mod_path/merlind
%_bindir/merlind
%_libdir/merlin/install-merlin.sh
%_sysconfdir/logrotate.d/merlin
%_sysconfdir/nrpe.d/nrpe-merlin.cfg
# TODO check for systemd?
%{_unitdir}/merlind.service
%attr(-, %daemon_user, %daemon_group) %dir %_localstatedir/lib/merlin
%attr(775, %daemon_user, %daemon_group) %dir %_localstatedir/lib/merlin/binlogs
%attr(-, %daemon_user, %daemon_group) %dir %_localstatedir/merlin
%attr(-, %daemon_user, %daemon_group) %dir %_localstatedir/run/merlin
%attr(-, %daemon_user, %daemon_group) %dir %_localstatedir/cache/merlin
%attr(-, %daemon_user, %daemon_group) %dir %_localstatedir/cache/merlin/config


%files -n monitor-merlin
%defattr(-,root,root)
%_libdir/merlin/merlin.*
%mod_path/merlin.so
%attr(-, %daemon_user, %daemon_group) /opt/monitor/etc/mconf/merlin.cfg
%attr(-, %daemon_user, %daemon_group) %dir %_localstatedir/lib/merlin
%attr(-, %daemon_user, %daemon_group) %dir %_localstatedir/log/merlin
%attr(0440, root, root) %{_sysconfdir}/sudoers.d/merlin

%files apps
%defattr(-,root,root)
%_libdir/merlin/import
%_libdir/merlin/showlog
%_libdir/merlin/rename
%_libdir/merlin/oconf
%_libdir/merlin/keygen
%mod_path/import
%mod_path/showlog
%mod_path/rename
%_libdir/merlin/mon
%_bindir/mon
%_bindir/op5

%attr(600, root, root) %_libdir/merlin/mon/syscheck/db_mysql_check.sh
%attr(600, root, root) %_libdir/merlin/mon/syscheck/fs_ext_state.sh

%exclude %_libdir/merlin/mon/test.py*
%exclude %_libdir/merlin/merlin.*

%if 0%{?rhel} >= 7
%files slim
%defattr(-,root,root)
%attr(660, -, %daemon_group) %config(noreplace) %mod_path/merlin.conf
%mod_path/merlind
%_bindir/merlind
%_libdir/merlin/install-merlin.sh
%_sysconfdir/logrotate.d/merlin
%_sysconfdir/nrpe.d/nrpe-merlin.cfg
%attr(-, %daemon_user, %daemon_group) %dir %_localstatedir/lib/merlin
%attr(775, %daemon_user, %daemon_group) %dir %_localstatedir/lib/merlin/binlogs
%attr(-, %daemon_user, %daemon_group) %dir %_localstatedir/log/merlin
%attr(-, %daemon_user, %daemon_group) %dir %_localstatedir/run/merlin
%attr(-, %daemon_user, %daemon_group) %dir %_localstatedir/cache/merlin
%attr(-, %daemon_user, %daemon_group) %dir %_localstatedir/cache/merlin/config

%files -n monitor-merlin-slim
%defattr(-,root,root)
%_libdir/merlin/merlin.*
%mod_path/merlin.so
%attr(-, %daemon_user, %daemon_group) %naemon_confdir/module-conf.d/merlin.cfg
%attr(-, %daemon_user, %daemon_group) %dir %_localstatedir/lib/merlin
%attr(-, %daemon_user, %daemon_group) %dir %_localstatedir/log/merlin
%attr(0440, root, root) %{_sysconfdir}/sudoers.d/merlin

%files apps-slim
%defattr(-,root,root)
%_libdir/merlin/oconf
%_libdir/merlin/mon
%_libdir/merlin/keygen
%_bindir/mon
%_bindir/op5

%attr(600, root, root) %_libdir/merlin/mon/syscheck/db_mysql_check.sh
%attr(600, root, root) %_libdir/merlin/mon/syscheck/fs_ext_state.sh

%exclude %_libdir/merlin/mon/test.py*
%exclude %_libdir/merlin/merlin.*
%endif

%files test
%defattr(-,root,root)
%_libdir/merlin/mon/test.py*
%_bindir/cukemerlin
/usr/share/merlin/app-tests/

%clean
rm -rf %buildroot

%changelog
* Thu Feb 11 2021 Aksel Sjögren <asjogren@itrsgroup.com>
- Adapt for building on el8.
* Tue Mar 17 2009 Andreas Ericsson <ae@op5.se>
- Initial specfile creation.
