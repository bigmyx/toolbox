guac_server         = "guacamole-server-#{node['guacamole']['version']}"
auth_jdbc_tar       = "guacamole-auth-jdbc-#{node['guacamole']['version']}.tar.gz"
mysql_connector_tar = "mysql-connector-java-5.1.38.tar.gz"

secret      = Chef::EncryptedDataBagItem.load_secret(Chef::Config[:encrypted_data_bag_secret])
mysql_creds = data_bag_item('passwords', 'mysql', secret)


%w[build-essential libpng12-dev libjpeg62-dev libcairo2-dev libossp-uuid-dev libfreerdp-dev libwebp-dev].each do |package|
  package package do
    action :install
  end
end

%w[/etc/guacamole /etc/guacamole/lib /etc/guacamole/extensions].each do |dir|
  directory dir
end

remote_file "#{Chef::Config[:file_cache_path]}/#{guac_server}.tar.gz" do
  source "https://sourceforge.net/projects/guacamole/files/current/source/#{guac_server}.tar.gz"
  mode '0644'
  action :create_if_missing
end

remote_file "#{Chef::Config[:file_cache_path]}/#{auth_jdbc_tar}" do
  source "http://sourceforge.net/projects/guacamole/files/current/extensions/#{auth_jdbc_tar}"
  mode '0644'
  action :create_if_missing
end

remote_file "#{Chef::Config[:file_cache_path]}/#{mysql_connector_tar}" do
  source "http://dev.mysql.com/get/Downloads/Connector/j/#{mysql_connector_tar}"
  mode '0644'
  action :create_if_missing
end

directory "/usr/lib/x86_64-linux-gnu/freerdp"

bash "build-and-install-guacamole" do
  cwd Chef::Config[:file_cache_path]
  code <<-EOF
    tar xzf #{guac_server}.tar.gz
    cd #{guac_server} && ./configure --with-init-dir=/etc/init.d
    make && make install
    ldconfig
  EOF
  creates "#{Chef::Config[:file_cache_path]}/#{guac_server}/config.log"
end

bash "extract and copy mysql-auth stuff" do
  cwd Chef::Config[:file_cache_path]
  code <<-EOF
  tar xzf #{auth_jdbc_tar}
  tar xzf #{mysql_connector_tar}
  ln -sf /usr/local/lib/freerdp/* /usr/lib/x86_64-linux-gnu/freerdp/.
  cp -f mysql-connector-java-5.1.38/mysql-connector-java-5.1.38-bin.jar /etc/guacamole/lib/
  cp -f guacamole-auth-jdbc-#{node['guacamole']['version']}/mysql/guacamole-auth-jdbc-mysql-#{node['guacamole']['version']}.jar /etc/guacamole/extensions/
  EOF
end

service 'guacd' do
  supports :restart => true, :reload => true
  action [ :enable, :start ]
end

template '/etc/guacamole/guacamole.properties' do
  source 'guacamole.properties.erb'
  variables(
    :mysql_user     => mysql_creds['user'],
    :mysql_password => mysql_creds['password'],
    :mysql_host     => mysql_creds['host']
  )
  mode '0644'
  notifies :restart, 'service[guacd]'
end

