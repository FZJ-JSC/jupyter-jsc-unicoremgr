from app import unicore_utils, utils_file_loads, tunnel_communication, hub_communication, orchestrator_communication,\
    unicore_communication
from app.utils import remove_secret


def quota_check(app_logger, uuidcode, app_urls, request_headers, unicore_header, cert, servername):
    try:
        method = "GET"
        method_args = {"url": request_headers.get('filedir')+'/.quota_check.out',
                       "headers": unicore_header,
                       "certificate": cert,
                       "return_content": True}
        content, status_code, response_header = unicore_communication.request(app_logger,
                                                                              uuidcode,
                                                                              method,
                                                                              method_args)
        if status_code != 200:
            app_logger.warning("uuidcode={} - Could not get hostname. UNICORE/X Response: {} {} {}".format(uuidcode, content, status_code, remove_secret(response_header)))
            raise Exception("{} - Could not get hostname. Throw exception because of wrong status_code: {}".format(uuidcode, status_code))
        else:
            unicore_header['X-UNICORE-SecuritySession'] = response_header['X-UNICORE-SecuritySession']
            quota_result = content.strip()
    except:
        app_logger.exception("uuidcode={} - Could not get hostname. {} {}".format(uuidcode, method, remove_secret(method_args)))
        app_logger.warning("uuidcode={} - Send cancel to JupyterHub.".format(uuidcode))
        hub_communication.cancel(app_logger,
                                 uuidcode,
                                 app_urls.get('hub', {}).get('url_proxy_route'),
                                 app_urls.get('hub', {}).get('url_cancel'),
                                 request_headers.get('jhubtoken'),
                                 "Something went wrong. An administrator is informed.",
                                 request_headers.get('escapedusername'),
                                 servername)
        return False
    if quota_result.lower() == "datausage" or quota_result.lower() == "inode":
        app_logger.info("uuidcode={} - Quota Check for user: Quota exceeded {}".format(uuidcode, quota_result))
        stop_job(app_logger,
                 uuidcode,
                 servername,
                 request_headers.get('system'),
                 request_headers,
                 app_urls,
                 True,
                 "Your disk quota in $HOME is exceeded. Please check it at https://judoor.fz-juelich.de or with this command: \"$ jutil user dataquota\".",
                 True,
                 False)
        return False
    elif quota_result.lower() == "ok":
        app_logger.debug("uuidcode={} - Quota Check for user ok".format(uuidcode))
        return True
    else:
        app_logger.info("uuidcode={} - Could not understand the quota result: {}".format(uuidcode, quota_result))
        return True


def stop_job(app_logger, uuidcode, servername, system, request_headers, app_urls, send_cancel=True, errormsg="", stop_unicore_job=True, kill_tunnel=True):
    app_logger.trace("uuidcode={} - Create UNICORE Header".format(uuidcode))
    if ':' not in servername:
        servername = "{}:{}".format(request_headers.get('escapedusername'), servername)
        
    if send_cancel:
        app_logger.debug("uuidcode={} - Send cancel to JupyterHub".format(uuidcode))
        hub_communication.cancel(app_logger,
                                 uuidcode,
                                 app_urls.get('hub', {}).get('url_proxy_route'),
                                 app_urls.get('hub', {}).get('url_cancel'),
                                 request_headers.get('jhubtoken'),
                                 errormsg,
                                 request_headers.get('escapedusername'),
                                 servername)
    unicore_header = {}
    accesstoken = ""
    expire = ""
    if stop_unicore_job:
        unicore_header, accesstoken, expire = unicore_utils.create_header(app_logger,
                                                                          uuidcode,
                                                                          request_headers,
                                                                          app_urls.get('hub', {}).get('url_proxy_route'),
                                                                          app_urls.get('hub', {}).get('url_token'),
                                                                          request_headers.get('escapedusername'),
                                                                          servername)
    
    
        # Get certificate path to communicate with UNICORE/X Server
        app_logger.trace("uuidcode={} - FileLoad: UNICORE/X certificate path".format(uuidcode))
        unicorex = utils_file_loads.get_unicorex()
        cert = unicorex.get(system, {}).get('certificate', False)
        app_logger.trace("uuidcode={} - FileLoad: UNICORE/X certificate path Result: {}".format(uuidcode, cert))
    
        # Get logs from the UNICORE workspace. Necessary for support
        app_logger.debug("uuidcode={} - Copy_log".format(uuidcode))
        try:
            unicore_utils.copy_log(app_logger,
                                   uuidcode,
                                   unicore_header,
                                   request_headers.get('filedir'),
                                   request_headers.get('kernelurl'),
                                   cert)
        except:
            app_logger.exception("uuidcode={} - Could not copy log.".format(uuidcode))
    
        # Abort the Job via UNICORE
        app_logger.debug("uuidcode={} - Abort Job".format(uuidcode))
        unicore_utils.abort_job(app_logger,
                                uuidcode,
                                request_headers.get('kernelurl'),
                                unicore_header,
                                cert)
        if unicorex.get(system, {}).get('destroyjobs', 'false').lower() == 'true':
            # Destroy the Job via UNICORE
            app_logger.debug("uuidcode={} - Destroy Job".format(uuidcode))
            unicore_utils.destroy_job(app_logger,
                                      uuidcode,
                                      request_headers.get('kernelurl'),
                                      unicore_header,
                                      cert)
        else:
            # if it's a cron job we want to delete it
            cron_info = utils_file_loads.get_cron_info()
            user, servernameshort = request_headers.get('servername', ':').split(':')  # @UnusedVariable
            if cron_info.get('systems', {}).get(request_headers.get('system').upper(), {}).get('servername', '<undefined>') == servernameshort:
                if cron_info.get('systems', {}).get(request_headers.get('system').upper(), {}).get('account', '<undefined>') == request_headers.get('account'):
                    if cron_info.get('systems', {}).get(request_headers.get('system').upper(), {}).get('project', '<undefined>') == request_headers.get('project'):
                        unicore_utils.destroy_job(app_logger,
                                                  uuidcode,
                                                  request_headers.get('kernelurl'),
                                                  unicore_header,
                                                  cert)
    
    # Kill the tunnel
    tunnel_info = { "servername": servername }
    if kill_tunnel:
        try:
            app_logger.debug("uuidcode={} - Close ssh tunnel".format(uuidcode))
            tunnel_communication.close(app_logger,
                                       uuidcode,
                                       app_urls.get('tunnel', {}).get('url_tunnel'),
                                       tunnel_info)
        except:
            app_logger.exception("uuidcode={} - Could not stop tunnel. tunnel_info: {} {}".format(uuidcode, tunnel_info, app_urls.get('tunnel', {}).get('url_tunnel')))

    # Remove Database entry for J4J_Orchestrator
    app_logger.debug("uuidcode={} - Call J4J_Orchestrator to remove entry {} from database".format(uuidcode, servername))
    orchestrator_communication.delete_database_entry(app_logger,
                                                     uuidcode,
                                                     app_urls.get('orchestrator', {}).get('url_database'),
                                                     servername)

    return accesstoken, expire, unicore_header.get('X-UNICORE-SecuritySession')
