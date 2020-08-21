from . import routes
from app import check_session, db, session, redirect, render_template, request, \
    config, send_log_data
from .project import check_project_access, check_project_archived
from forms import *
from libnmap.parser import NmapParser
from libnessus.parser import NessusParser
import json
import csv
import codecs
import re
from bs4 import BeautifulSoup
import urllib.parse
from IPy import IP
import socket


@routes.route('/project/<uuid:project_id>/tools/', methods=['GET'])
@check_session
@check_project_access
@check_project_archived
@send_log_data
def project_tools(project_id, current_project, current_user):
    return render_template('project-pages/tools/toolslist.html',
                           current_project=current_project)


@routes.route('/project/<uuid:project_id>/tools/nmap/', methods=['GET'])
@check_session
@check_project_access
@check_project_archived
@send_log_data
def nmap_page(project_id, current_project, current_user):
    return render_template('project-pages/tools/import-scan/nmap.html',
                           current_project=current_project)


@routes.route('/project/<uuid:project_id>/tools/nmap/', methods=['POST'])
@check_session
@check_project_access
@check_project_archived
@send_log_data
def nmap_page_form(project_id, current_project, current_user):
    form = NmapForm()
    form.validate()
    errors = []
    if form.errors:
        for field in form.errors:
            for error in form.errors[field]:
                errors.append(error)

    if not errors:
        add_empty_hosts = form.add_no_open.data
        for file in form.files.data:
            xml_report_data = file.read().decode('charmap')
            nmap_report = NmapParser.parse_fromstring(xml_report_data)
            try:
                command_str = nmap_report.commandline
            except:
                command_str = ''
            for host in nmap_report.hosts:
                # check if we will add host
                found = 0
                for service in host.services:
                    if service.state == 'open':
                        found = 1
                    elif service.state == 'filtered' and \
                            form.rule.data in ['filtered', 'closed']:
                        found = 1
                    elif service.state == 'closed' and form.rule.data == 'closed':
                        found = 1
                if found or add_empty_hosts:
                    host_id = db.select_project_host_by_ip(
                        current_project['id'], host.address)
                    if not host_id:
                        host_id = db.insert_host(current_project['id'],
                                                 host.address,
                                                 current_user['id'],
                                                 current_project,
                                                 'Added from NMAP scan')
                    else:
                        host_id = host_id[0]['id']
                    for hostname in host.hostnames:
                        if hostname and hostname != host.address:
                            hostname_id = db.select_ip_hostname(host_id,
                                                                hostname)
                            if not hostname_id:
                                hostname_id = db.insert_hostname(host_id,
                                                                 hostname,
                                                                 'Added from NMAP scan',
                                                                 current_user[
                                                                     'id'])
                            else:
                                hostname_id = hostname_id[0]['id']
                    for service in host.services:
                        is_tcp = service.protocol == 'tcp'
                        service_name = service.service
                        service_banner = service.banner
                        add = 0
                        if service.state == 'open':
                            add = 1
                        elif service.state == 'filtered' and \
                            form.rule.data in ['filtered','closed']:
                            add = 1
                            service_banner += '\nstate: filtered'
                        elif service.state == 'closed' and \
                            form.rule.data == 'closed':
                            add = 1
                            service_banner += '\nstate: closed'
                        if add == 1:
                            port_id = db.select_ip_port(host_id, service.port,
                                                        is_tcp)
                            if not port_id:
                                port_id = db.insert_host_port(host_id,
                                                              service.port,
                                                              is_tcp,
                                                              service_name,
                                                              service_banner,
                                                              current_user['id'],
                                                              current_project['id'])
                            else:
                                port_id = port_id[0]['id']
                                db.update_port_proto_description(port_id,
                                                                 service_name,
                                                                 service_banner)

    return render_template('project-pages/tools/import-scan/nmap.html',
                           current_project=current_project,
                           errors=errors,
                           success=1)


@routes.route('/project/<uuid:project_id>/tools/nessus/', methods=['GET'])
@check_session
@check_project_access
@check_project_archived
@send_log_data
def nessus_page(project_id, current_project, current_user):
    return render_template('project-pages/tools/import-scan/nessus.html',
                           current_project=current_project)


@routes.route('/project/<uuid:project_id>/tools/nessus/', methods=['POST'])
@check_session
@check_project_access
@check_project_archived
@send_log_data
def nessus_page_form(project_id, current_project, current_user):
    form = NessusForm()
    form.validate()
    errors = []
    if form.errors:
        for field in form.errors:
            for error in form.errors[field]:
                errors.append(error)

    if not errors:
        add_info_issues = form.add_info_issues.data
        # xml files
        for file in form.xml_files.data:
            if file.filename:
                xml_report_data = file.read().decode('charmap')
                scan_result = NessusParser.parse_fromstring(xml_report_data)
                for host in scan_result.hosts:
                    host_id = db.select_project_host_by_ip(
                        current_project['id'], host.address)
                    if not host_id:
                        host_id = db.insert_host(current_project['id'],
                                                 host.address,
                                                 current_user['id'],
                                                 current_project,
                                                 'Added from Nessus scan')
                    else:
                        host_id = host_id[0]['id']

                    # add hostname
                    hostname_id = ''
                    if host.name and host.name != host.address:
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
                        if hostname_id:
                            services = {port_id: ['0', hostname_id]}
                        else:
                            services = {port_id: ['0']}
                        if cvss > 0 or (cvss == 0 and add_info_issues):
                            db.insert_new_issue(name, description, '', cvss,
                                                current_user['id'], services,
                                                'need to check',
                                                current_project['id'],
                                                cve)
        # csv files
        for file in form.csv_files.data:
            if file.filename:
                scan_result = csv.DictReader(codecs.iterdecode(file, 'charmap'),
                                             delimiter=',')

                for row in scan_result:
                    cve = row['CVE'] if row['CVE'] else 0
                    cvss = float(row['CVSS']) if row['CVSS'] else 0
                    host = row['Host']
                    port = int(row['Port'])
                    name = row['Name']
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
                        host_id = db.insert_host(current_project['id'],
                                                 host,
                                                 current_user['id'],
                                                 current_project,
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
                    if cvss > 0 or (cvss == 0 and add_info_issues):
                        db.insert_new_issue(name, full_description, '', cvss,
                                            current_user['id'], services,
                                            'need to check',
                                            current_project['id'],
                                            cve,
                                            cwe)

    return render_template('project-pages/tools/import-scan/nessus.html',
                           current_project=current_project,
                           errors=errors)


@routes.route('/project/<uuid:project_id>/tools/nikto/', methods=['GET'])
@check_session
@check_project_access
@check_project_archived
@send_log_data
def nikto_page(project_id, current_project, current_user):
    return render_template('project-pages/tools/import-scan/nikto.html',
                           current_project=current_project)


@routes.route('/project/<uuid:project_id>/tools/nikto/', methods=['POST'])
@check_session
@check_project_access
@check_project_archived
@send_log_data
def nikto_page_form(project_id, current_project, current_user):
    form = NiktoForm()
    form.validate()
    errors = []
    if form.errors:
        for field in form.errors:
            for error in form.errors[field]:
                errors.append(error)

    if not errors:
        # json files
        for file in form.json_files.data:
            if file.filename:
                json_report_data = file.read().decode('charmap').replace(',]',
                                                                         ']').replace(
                    ',}', '}')
                scan_result = json.loads(json_report_data)
                host = scan_result['ip']
                hostname = scan_result['host'] if scan_result['ip'] != \
                                                  scan_result['host'] else ''
                issues = scan_result['vulnerabilities']
                port = int(scan_result['port'])
                protocol = 'https' if '443' in str(port) else 'http'
                is_tcp = 1
                port_description = 'Added by Nikto scan'
                if scan_result['banner']:
                    port_description = 'Nikto banner: {}'.format(
                        scan_result['banner'])

                # add host
                host_id = db.select_project_host_by_ip(current_project['id'],
                                                       host)
                if not host_id:
                    host_id = db.insert_host(current_project['id'],
                                             host,
                                             current_user['id'],
                                             current_project,
                                             'Added by Nikto scan')
                else:
                    host_id = host_id[0]['id']

                # add hostname

                hostname_id = ''
                if hostname and hostname != host:
                    hostname_id = db.select_ip_hostname(host_id, hostname)
                    if not hostname_id:
                        hostname_id = db.insert_hostname(host_id,
                                                         hostname,
                                                         'Added from Nikto scan',
                                                         current_user['id'])
                    else:
                        hostname_id = hostname_id[0]['id']

                # add port
                port_id = db.select_ip_port(host_id, port, is_tcp)
                if not port_id:
                    port_id = db.insert_host_port(host_id,
                                                  port,
                                                  is_tcp,
                                                  protocol,
                                                  port_description,
                                                  current_user['id'],
                                                  current_project['id'])
                else:
                    port_id = port_id[0]['id']

                for issue in issues:
                    method = issue['method']
                    url = issue['url']
                    full_url = '{} {}'.format(method, url)
                    osvdb = int(issue['OSVDB'])
                    info = issue['msg']
                    full_info = 'OSVDB: {}\n\n{}'.format(osvdb, info)

                    services = {port_id: ['0']}
                    if hostname_id:
                        services = {port_id: ['0', hostname_id]}

                    db.insert_new_issue('Nikto scan', full_info, full_url, 0,
                                        current_user['id'], services,
                                        'need to check',
                                        current_project['id'],
                                        cve=0,
                                        cwe=0,
                                        )
        # csv load
        for file in form.csv_files.data:
            if file.filename:
                scan_result = csv.reader(codecs.iterdecode(file, 'charmap'),
                                         delimiter=',')

                for issue in scan_result:
                    if len(issue) == 7:
                        hostname = issue[0]
                        host = issue[1]
                        port = int(issue[2])
                        protocol = 'https' if '443' in str(port) else 'http'
                        is_tcp = 1
                        osvdb = issue[3]
                        full_url = '{} {}'.format(issue[4], issue[5])
                        full_info = 'OSVDB: {}\n{}'.format(osvdb, issue[6])

                        # add host
                        host_id = db.select_project_host_by_ip(
                            current_project['id'],
                            host)
                        if not host_id:
                            host_id = db.insert_host(current_project['id'],
                                                     host,
                                                     current_user['id'],
                                                     current_project,
                                                     'Added by Nikto scan')
                        else:
                            host_id = host_id[0]['id']

                        # add hostname
                        hostname_id = ''
                        if hostname and hostname != host:
                            hostname_id = db.select_ip_hostname(host_id,
                                                                hostname)
                            if not hostname_id:
                                hostname_id = db.insert_hostname(host_id,
                                                                 hostname,
                                                                 'Added from Nikto scan',
                                                                 current_user[
                                                                     'id'])
                            else:
                                hostname_id = hostname_id[0]['id']

                        # add port
                        port_id = db.select_ip_port(host_id, port, is_tcp)
                        if not port_id:
                            port_id = db.insert_host_port(host_id,
                                                          port,
                                                          is_tcp,
                                                          protocol,
                                                          'Added from Nikto scan',
                                                          current_user['id'],
                                                          current_project['id'])
                        else:
                            port_id = port_id[0]['id']

                        # add issue
                        services = {port_id: ['0']}
                        if hostname_id:
                            services = {port_id: ['0', hostname_id]}

                        db.insert_new_issue('Nikto scan', full_info, full_url,
                                            0,
                                            current_user['id'], services,
                                            'need to check',
                                            current_project['id'],
                                            cve=0,
                                            cwe=0,
                                            )

        for file in form.xml_files.data:
            if file.filename:
                scan_result = BeautifulSoup(file.read(),
                                            "html.parser").niktoscan.scandetails
                host = scan_result['targetip']
                port = int(scan_result['targetport'])
                is_tcp = 1
                port_banner = scan_result['targetbanner']
                hostname = scan_result['targethostname']
                issues = scan_result.findAll("item")
                protocol = 'https' if '443' in str(port) else 'http'
                port_description = ''
                if port_banner:
                    port_description = 'Nikto banner: {}'.format(
                        scan_result['targetbanner'])

                # add host
                host_id = db.select_project_host_by_ip(
                    current_project['id'],
                    host)
                if not host_id:
                    host_id = db.insert_host(current_project['id'],
                                             host,
                                             current_user['id'],
                                             current_project,
                                             'Added by Nikto scan')
                else:
                    host_id = host_id[0]['id']

                # add hostname
                hostname_id = ''
                if hostname and hostname != host:
                    hostname_id = db.select_ip_hostname(host_id,
                                                        hostname)
                    if not hostname_id:
                        hostname_id = db.insert_hostname(host_id,
                                                         hostname,
                                                         'Added from Nikto scan',
                                                         current_user[
                                                             'id'])
                    else:
                        hostname_id = hostname_id[0]['id']

                # add port
                port_id = db.select_ip_port(host_id, port, is_tcp)
                if not port_id:
                    port_id = db.insert_host_port(host_id,
                                                  port,
                                                  is_tcp,
                                                  protocol,
                                                  port_description,
                                                  current_user['id'],
                                                  current_project['id'])
                else:
                    port_id = port_id[0]['id']

                for issue in issues:
                    method = issue['method']
                    url = issue.uri.contents[0]
                    full_url = '{} {}'.format(method, url)
                    osvdb = int(issue['osvdbid'])
                    info = issue.description.contents[0]
                    full_info = 'OSVDB: {}\n\n{}'.format(osvdb, info)

                    services = {port_id: ['0']}
                    if hostname_id:
                        services = {port_id: ['0', hostname_id]}

                    db.insert_new_issue('Nikto scan', full_info, full_url, 0,
                                        current_user['id'], services,
                                        'need to check',
                                        current_project['id'],
                                        cve=0,
                                        cwe=0,
                                        )

    return render_template('project-pages/tools/import-scan/nikto.html',
                           current_project=current_project)


@routes.route('/project/<uuid:project_id>/tools/acunetix/', methods=['GET'])
@check_session
@check_project_access
@check_project_archived
@send_log_data
def acunetix_page(project_id, current_project, current_user):
    return render_template('project-pages/tools/import-scan/acunetix.html',
                           current_project=current_project)


@routes.route('/project/<uuid:project_id>/tools/acunetix/', methods=['POST'])
@check_session
@check_project_access
@check_project_archived
@send_log_data
def acunetix_page_form(project_id, current_project, current_user):
    form = AcunetixForm()
    form.validate()
    errors = []
    if form.errors:
        for field in form.errors:
            for error in form.errors[field]:
                errors.append(error)

    if not errors:
        auto_resolve = form.auto_resolve.data == 1

        # xml files
        for file in form.files.data:
            if file.filename:
                scan_result = BeautifulSoup(file.read(),
                                            "html.parser").scangroup.scan
                start_url = scan_result.starturl.contents[0]
                parsed_url = urllib.parse.urlparse(start_url)
                protocol = parsed_url.scheme
                hostname = parsed_url.hostname
                port = parsed_url.port
                os_descr = scan_result.os.contents[0]
                port_banner = scan_result.banner.contents[0]
                web_banner = scan_result.webserver.contents[0]
                port_description = 'Banner: {} Web: {}'.format(port_banner,
                                                               web_banner)
                host_description = 'OS: {}'.format(os_descr)
                is_tcp = 1
                if not port:
                    port = 80 if protocol == 'http' else 443

                try:
                    IP(hostname)
                    host = hostname
                    hostname = ''
                except:
                    if form.host.data:
                        IP(form.host.data)
                        host = form.host.data
                    elif form.auto_resolve.data == 1:
                        host = socket.gethostbyname(hostname)
                    else:
                        errors.append('ip not resolved!')

                if not errors:
                    # add host
                    host_id = db.select_project_host_by_ip(
                        current_project['id'],
                        host)
                    if not host_id:
                        host_id = db.insert_host(current_project['id'],
                                                 host,
                                                 current_user['id'],
                                                 current_project,
                                                 host_description)
                    else:
                        host_id = host_id[0]['id']
                        db.update_host_description(host_id, host_description)

                    # add hostname
                    hostname_id = ''
                    if hostname and hostname != host:
                        hostname_id = db.select_ip_hostname(host_id,
                                                            hostname)
                        if not hostname_id:
                            hostname_id = db.insert_hostname(host_id,
                                                             hostname,
                                                             'Added from Acunetix scan',
                                                             current_user['id'])
                        else:
                            hostname_id = hostname_id[0]['id']

                    # add port
                    port_id = db.select_ip_port(host_id, port, is_tcp)
                    if not port_id:
                        port_id = db.insert_host_port(host_id,
                                                      port,
                                                      is_tcp,
                                                      protocol,
                                                      port_description,
                                                      current_user['id'],
                                                      current_project['id'])
                    else:
                        port_id = port_id[0]['id']
                        db.update_port_proto_description(port_id, protocol,
                                                         port_description)
                    issues = scan_result.reportitems.findAll("reportitem")

                    for issue in issues:
                        issue_name = issue.contents[1].contents[0]
                        module_name = issue.modulename.contents[0]
                        uri = issue.affects.contents[0]
                        request_params = issue.parameter.contents[0]
                        full_uri = '{} params:{}'.format(uri, request_params)
                        impact = issue.impact.contents[0]
                        issue_description = issue.description.contents[0]
                        recomendations = issue.recommendation.contents[0]
                        issue_request = issue.technicaldetails.request.contents[
                            0]
                        cwe = int(issue.cwe['id'].replace('CWE-', ''))
                        cvss = float(issue.cvss.score.contents[0])
                        # TODO: check CVE field

                        full_info = '''Module: \n{}\n\nDescription: \n{}\n\nImpact: \n{}\n\nRecomendations: \n{}\n\nRequest: \n{}'''.format(
                            module_name, issue_description, impact,
                            recomendations, issue_request)

                        services = {port_id: ['0']}
                        if hostname_id:
                            services = {port_id: ['0', hostname_id]}

                        db.insert_new_issue(issue_name,
                                            full_info, full_uri,
                                            cvss,
                                            current_user['id'], services,
                                            'need to check',
                                            current_project['id'],
                                            cve=0,
                                            cwe=cwe
                                            )
    return render_template('project-pages/tools/import-scan/acunetix.html',
                           current_project=current_project)
