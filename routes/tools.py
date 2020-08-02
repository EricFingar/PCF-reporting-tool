from . import routes
from app import check_session, db, session, redirect, render_template, request, \
    config, url_for
from .project import check_project_access, check_project_archived
from forms import *
from libnmap.parser import NmapParser
from libnessus.parser import NessusParser
import json
import csv
import codecs


@routes.route('/project/<uuid:project_id>/tools/', methods=['GET'])
@check_session
@check_project_access
@check_project_archived
def project_tools(project_id, current_project, current_user):
    return render_template('project-pages/tools/toolslist.html',
                           current_project=current_project)


@routes.route('/project/<uuid:project_id>/tools/nmap/', methods=['GET'])
@check_session
@check_project_access
@check_project_archived
def nmap_page(project_id, current_project, current_user):
    return render_template('project-pages/tools/import-scan/nmap.html',
                           current_project=current_project)


@routes.route('/project/<uuid:project_id>/tools/nmap/', methods=['POST'])
@check_session
@check_project_access
@check_project_archived
def nmap_page_form(project_id, current_project, current_user):
    form = NmapForm()
    form.validate()
    errors = []
    if form.errors:
        for field in form.errors:
            for error in form.errors[field]:
                errors += error

    if not errors:
        add_empty_hosts = form.add_no_open.data
        for file in form.files.data:
            xml_report_data = file.read().decode('charmap')
            nmap_report = NmapParser.parse_fromstring(xml_report_data)
            command_str = nmap_report.commandline
            for host in nmap_report.hosts:
                if host.services or add_empty_hosts:
                    host_id = db.select_project_host_by_ip(
                        current_project['id'], host.address)
                    if not host_id:
                        host_id = db.insert_new_ip(current_project['id'],
                                                   host.address,
                                                   current_user['id'],
                                                   'Added from NMAP scan')
                    else:
                        host_id = host_id[0]['id']
                    for hostname in host.hostnames:
                        hostname_id = db.select_ip_hostname(host_id, hostname)
                        if not hostname_id:
                            hostname_id = db.insert_hostname(host_id,
                                                             hostname,
                                                             'Added from NMAP scan',
                                                             current_user['id'])
                        else:
                            hostname_id = hostname_id[0]['id']
                    for service in host.services:
                        is_tcp = service.protocol == 'tcp'
                        port_id = db.select_ip_port(host_id, service.port,
                                                    is_tcp)
                        if not port_id:
                            port_id = db.insert_host_port(host_id,
                                                          service.port,
                                                          is_tcp,
                                                          service.service,
                                                          service.banner,
                                                          current_user['id'],
                                                          current_project['id'])
                        else:
                            port_id = port_id[0]['id']
                            db.update_port_proto_description(port_id,
                                                             service.service,
                                                             service.banner)

    return render_template('project-pages/tools/import-scan/nmap.html',
                           current_project=current_project,
                           errors=errors)


@routes.route('/project/<uuid:project_id>/tools/nessus/', methods=['GET'])
@check_session
@check_project_access
@check_project_archived
def nessus_page(project_id, current_project, current_user):
    return render_template('project-pages/tools/import-scan/nessus.html',
                           current_project=current_project)


@routes.route('/project/<uuid:project_id>/tools/nessus/', methods=['POST'])
@check_session
@check_project_access
@check_project_archived
def nessus_page_form(project_id, current_project, current_user):
    form = NessusForm()
    form.validate()
    errors = []
    if form.errors:
        for field in form.errors:
            for error in form.errors[field]:
                errors += error

    if not errors:
        # xml files
        for file in form.xml_files.data:
            if file.filename:
                xml_report_data = file.read().decode('charmap')
                scan_result = NessusParser.parse_fromstring(xml_report_data)
                for host in scan_result.hosts:
                    host_id = db.select_project_host_by_ip(
                        current_project['id'], host.address)
                    if not host_id:
                        host_id = db.insert_new_ip(current_project['id'],
                                                   host.address,
                                                   current_user['id'],
                                                   'Added from Nessus scan')
                    else:
                        host_id = host_id[0]['id']

                    # add hostname
                    hostname_id = db.select_ip_hostname(host_id, host.name)
                    if not hostname_id:
                        hostname_id = db.insert_hostname(host_id,
                                                         host.name,
                                                         'Added from Nessus scan',
                                                         current_user['id'])
                    else:
                        hostname_id = hostname_id[0]['id']

                    for issue in host.get_report_items:

                        # create port

                        is_tcp = issue.protocol == 'tcp'
                        port_id = db.select_ip_port(host_id, int(issue.port),
                                                    is_tcp)
                        if not port_id:
                            port_id = db.insert_host_port(host_id,
                                                          issue.port,
                                                          is_tcp,
                                                          issue.service,
                                                          'Added from Nessus scan',
                                                          current_user['id'],
                                                          current_project['id'])
                        else:
                            port_id = port_id[0]['id']
                            db.update_port_service(port_id,
                                                   issue.service)
                        # add issue to created port

                        name = 'Nessus: {}'.format(issue.plugin_name)
                        description = 'Plugin name: {}\r\n\r\nInfo: \r\n{}\r\n\r\nSolution:\r\n {} \r\n\r\nOutput: \r\n {}'.format(
                            issue.plugin_name,
                            issue.synopsis,
                            issue.solution,
                            issue.get_vuln_info['plugin_output'].strip('\n'))
                        cve = issue.cve if issue.cve else 0
                        cvss = float(issue.severity)
                        services = {port_id: ['0', hostname_id]}
                        db.insert_new_issue(name, description, '', cvss,
                                            current_user['id'], services,
                                            'need to check',
                                            current_project['id'],
                                            cve)
        # csv files
        for file in form.csv_files.data:
            if file.filename:
                scan_result = csv.DictReader(codecs.iterdecode(file, 'charmap'), delimiter=',')

                for row in scan_result:
                    cve = row['CVE'] if row['CVE'] else 0
                    cvss = float(row['CVSS']) if row['CVSS'] else 0
                    host = row['Host']
                    port = int(row['Port'])
                    name = 'Nessus: {}'.format(row['Name'])
                    info = row['Synopsis']
                    decription = row['Description']
                    solution = row['Solution']
                    output = row['Plugin Output']
                    is_tcp = 1 if port == 0 else row['Protocol'] == 'tcp'
                    full_description = 'Plugin name: {}\r\n\r\nInfo: \r\n{}\r\n\r\nSolution:\r\n {} \r\n\r\nOutput: \r\n {}'.format(
                            name,
                            info,
                            solution,
                            output.strip('\n'))
                    try:
                        cwe = int(row['XREF'].replace('CWE:'))
                    except:
                        cwe = 0

                    # adding info
                    host_id = db.select_project_host_by_ip(
                        current_project['id'], host)
                    if not host_id:
                        host_id = db.insert_new_ip(current_project['id'],
                                                   host,
                                                   current_user['id'],
                                                   'Added from Nessus scan')
                    else:
                        host_id = host_id[0]['id']

                    port_id = db.select_ip_port(host_id, int(port), is_tcp)
                    if not port_id:
                        port_id = db.insert_host_port(host_id,
                                                      port,
                                                      is_tcp,
                                                      '',
                                                      'Added from Nessus scan',
                                                      current_user['id'],
                                                      current_project['id'])
                    else:
                        port_id = port_id[0]['id']

                    services = {port_id: ['0']}
                    db.insert_new_issue(name, full_description, '', cvss,
                                        current_user['id'], services,
                                        'need to check',
                                        current_project['id'],
                                        cve,
                                        cwe)

    return render_template('project-pages/tools/import-scan/nessus.html',
                           current_project=current_project,
                           errors=errors)
