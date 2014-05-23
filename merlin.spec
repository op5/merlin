%define mod_path /opt/monitor/op5/merlin
%define nagios_cfg /opt/monitor/etc/nagios.cfg

%define install_args --batch --dest-dir=%mod_path \\\
	--bindir=%_bindir --libexecdir=%_libdir/merlin --nagios-cfg=%nagios_cfg

%if 0%{?suse_version}
%define mysqld mysql
%define mysql_rpm mysql
%else
%define mysqld mysqld
%define mysql_rpm mysql-server
%endif

%{?dgroup:%define daemon_group %{dgroup}}

Summary: The merlin daemon is a multiplexing event-transport program
Name: merlin
Version: %{op5version}
Release: %{op5release}%{?dist}
License: GPLv2
Group: op5/Monitor
URL: http://www.op5.se
Source0: %name-%version.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}
Prefix: /opt/monitor
Requires: libaio
Requires: merlin-apps >= %version
Requires: monitor-config
Requires: op5-mysql
BuildRequires: mysql-devel
BuildRequires: op5-nagios-devel >= 3.99.99.7
Obsoletes: monitor-reports-module
BuildRequires: check-devel

%if 0%{?suse_version}
BuildRequires: libdbi-devel
BuildRequires: pkg-config
Requires: libdbi1
Requires: libdbi-drivers-dbd-mysql
Requires(post): mysql-client
%else
BuildRequires: libdbi-devel
BuildRequires: pkgconfig
Requires: libdbi
Requires: libdbi-dbd-mysql
%endif


%description
The merlin daemon is a multiplexing event-transport program designed to
link multiple Nagios instances together. It can also inject status
data into a variety of databases, using libdbi.


%package -n monitor-merlin
Summary: A Nagios module designed to communicate with the Merlin daemon
Group: op5/Monitor
Requires: op5-nagios >= 3.99.99.7, merlin = %version-%release
Requires: monitor-config
Requires: op5-monitor-supported-database

%description -n monitor-merlin
monitor-merlin is an event broker module running inside Nagios. Its
only purpose in life is to send events from the Nagios core to the
merlin daemon, which then takes appropriate action.


%package apps
Summary: Applications used to set up and aid a merlin/ninja installation
Group: op5/Monitor
Requires: rsync
Requires: op5-monitor-supported-database
%if 0%{?suse_version}
Requires: libdbi1
Requires: python-mysql
%else
%if 0%{?rhel} <= 5
Requires: python26
Requires: python26-mysqldb
%else
Requires: MySQL-python
%endif
Requires: libdbi
%endif
Obsoletes: monitor-distributed

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

%package test
Summary: Test files for merlin
Group: op5/Monitor
Requires: monitor-livestatus
Requires: op5-nagios
Requires: merlin merlin-apps monitor-merlin

%description test
Some additional test files for merlin

%prep
%setup -q

%build
sed -i 's/^DEF_VER=.*/DEF_VER=%{version}-%{release}/' gen-version.sh

# If we're building for CentOS 5 we have some sed'ing to do
%if ( ! 0%{?suse_version} ) && ( 0%{?rhel} <= 5 )
# use python26 for 'mon'
sed -i '1s#/bin/python.*#/bin/python26#' apps/mon.py
%endif


make ENABLE_LIBDBI=1 NAGIOS_PREFIX=/opt/monitor
make ENABLE_LIBDBI=1 NAGIOS_PREFIX=/opt/monitor test


%install
rm -rf %buildroot
sh install-merlin.sh %install_args --root=%buildroot --install=files,apps,init

chmod 777 %buildroot/%mod_path/logs
mkdir -p %buildroot/%mod_path/binlogs
mkdir -p %buildroot%_sysconfdir/logrotate.d
cp merlin.logrotate %buildroot%_sysconfdir/logrotate.d/merlin
ln -s ../../../../usr/bin/merlind %buildroot/%mod_path/merlind
ln -s ../../../../%_libdir/merlin/import %buildroot/%mod_path/import
ln -s ../../../../%_libdir/merlin/ocimp %buildroot/%mod_path/ocimp
ln -s ../../../../%_libdir/merlin/showlog %buildroot/%mod_path/showlog
ln -s ../../../../%_libdir/merlin/merlin.so %buildroot/%mod_path/merlin.so

# install plugins and create their symlinks
mkdir -p %buildroot/opt
cp -r apps/plugins %buildroot/opt
chmod 755 %buildroot/opt/plugins/*
for path in %buildroot/opt/plugins/*; do
	full_f=${path##*/}
	f=${full_f%.*}
	ln -s $full_f %buildroot/opt/plugins/$f
done

# install crontabs
mkdir -p %buildroot%_sysconfdir/cron.d
cp apps/*.cron %buildroot%_sysconfdir/cron.d/

mkdir -p %buildroot/opt/monitor/op5/nacoma/hooks/save/
sed -i 's#@@LIBEXECDIR@@#%_libdir/merlin#' op5build/nacoma_hook.py
install -m 0755 op5build/nacoma_hook.py %buildroot/opt/monitor/op5/nacoma/hooks/save/merlin_hook.py

mkdir -p %buildroot%_sysconfdir/op5kad/conf.d
cp kad.conf %buildroot%_sysconfdir/op5kad/conf.d/merlin.kad

mkdir -p %buildroot%_sysconfdir/nrpe.d
cp nrpe-merlin.cfg %buildroot%_sysconfdir/nrpe.d


%post
# we must stop the merlin deamon so it doesn't interfere with any
# database upgrades, logfile imports and whatnot
/etc/init.d/merlind stop >/dev/null || :

# Verify that mysql-server is installed and running before executing sql scripts
service %mysqld status 2&>1 >/dev/null
if [ $? -gt 0 ]; then
  echo "Attempting to start %mysqld..."
  service %mysqld start
  if [ $? -gt 0 ]; then
    echo "Abort: Failed to start %mysqld."
    exit 1
  fi
fi

$(mysql -Be "quit" 2>/dev/null) && MYSQL_AVAILABLE=1
if [ -n "$MYSQL_AVAILABLE" ]; then
  %mod_path/install-merlin.sh %install_args --batch --install=db
else
  echo "Can't login to %mysqld, probably because you have a root password set, bailing out..."
  exit 1
fi

# If mysql-server is running _or_ this is an upgrade
# we import logs
if [ $1 -eq 2 ]; then
  /sbin/chkconfig --add merlind || :
  echo "Importing status events from logfiles to database"
  mon log import --incremental || :
  echo "Importing notifications from logfiles to database"
  mon log import --only-notifications --incremental || :
fi

# restart all daemons
for daemon in merlind op5kad nrpe; do
	test -f /etc/init.d/$daemon && /etc/init.d/$daemon restart || :
done


%pre -n monitor-merlin
# If we're upgrading the module while Nagios makes a call
# into it, we'll end up with a core-dump due to some weirdness
# in dlopen(). If we're installing anew, we need to update the
# config and then restart. Either way, it's safe to stop it
# unconditionally here
sh /etc/init.d/monitor stop || :
sh /etc/init.d/monitor slay || :

%preun -n monitor-merlin
if [ $1 -eq 0 ]; then
	# removing the merlin module entirely
	sh /etc/init.d/monitor stop || :
	sh /etc/init.d/monitor slay || :
	sed -i /merlin.so/d %prefix/etc/nagios.cfg
	sh /etc/init.d/monitor start || :
	sh /etc/init.d/merlind stop || :
fi

%post -n monitor-merlin
sed -i 's#import_program = /opt/monitor/op5/merlin/import.php#import_program = /opt/monitor/op5/merlin/ocimp#g' %mod_path/merlin.conf
%mod_path/install-merlin.sh %install_args --install=config || :
sh /etc/init.d/monitor start || :


%files
%defattr(-,root,root)
%config(noreplace) %mod_path/merlin.conf
%mod_path/sample.merlin.conf
%mod_path/sql
%mod_path/merlind
%mod_path/install-merlin.sh
%_sysconfdir/logrotate.d/merlin
%_sysconfdir/op5kad/conf.d/merlin.kad
%_sysconfdir/nrpe.d/nrpe-merlin.cfg
/etc/init.d/merlind
%dir %mod_path
%dir %mod_path/logs
%mod_path/binlogs
/usr/bin/merlind


%files -n monitor-merlin
%defattr(-,root,root)
%mod_path/merlin.so
%_libdir/merlin/merlin.so


%files apps
%defattr(-,root,root)
%mod_path/import
%mod_path/showlog
%mod_path/ocimp
%mod_path/rename
%_libdir/merlin/*
%_bindir/mon
%_sysconfdir/cron.d/*
/opt/plugins/*
/opt/monitor/op5/nacoma/hooks/save/merlin_hook.py*

%exclude %_libdir/merlin/mon/test.py*
%exclude %_libdir/merlin/mon/run-ci-test.sh
%exclude %_libdir/merlin/merlin.so

%files test
%_libdir/merlin/mon/test.py*
%_libdir/merlin/mon/run-ci-test.sh

%clean
rm -rf %buildroot

%changelog
* Tue Mar 17 2009 Andreas Ericsson <ae@op5.se>
- Initial specfile creation.