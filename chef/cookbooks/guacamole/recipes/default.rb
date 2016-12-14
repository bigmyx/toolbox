# Installs and configures Guacamole server and it's Tomcat client

include_recipe "apt"
include_recipe "guacamole::guacd"
include_recipe "guacamole::tomcat_client"
