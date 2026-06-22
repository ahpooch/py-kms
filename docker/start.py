#!/usr/bin/python3 -u

# This replaces the old start.sh and ensures all arguments are bound correctly from the environment variables...
import logging
import os
import subprocess
import sys
import time

PYTHON3 = '/usr/bin/python3'
argumentVariableMapping = {
  '-l': 'LCID',
  '-c': 'CLIENT_COUNT',
  '-a': 'ACTIVATION_INTERVAL',
  '-r': 'RENEWAL_INTERVAL',
  '-w': 'HWID',
  '-V': 'LOGLEVEL',
  '-F': 'LOGFILE',
  '-S': 'LOGSIZE',
  '-e': 'EPID'
}

db_path = os.path.join(os.sep, 'home', 'py-kms', 'db', 'pykms_database.db')
log_file = os.environ.get('LOGFILE', 'STDOUT')
listen_ip = os.environ.get('IP', '::').split()
listen_port = os.environ.get('PORT', '1688')
want_webui = os.environ.get('WEBUI', '0') == '1'
want_metrics = os.environ.get('METRICS', '0') == '1'
webui_port = os.environ.get('WEBUI_PORT', '8080')
metrics_port = os.environ.get('METRICS_PORT', '9090')

def start_kms(logger):
  # Make sure the full path to the db exists
  if want_webui and not os.path.exists(os.path.dirname(db_path)):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

  # Build the command to execute
  command = [PYTHON3, '-u', 'pykms_Server.py', listen_ip[0], listen_port]
  for (arg, env) in argumentVariableMapping.items():
    if env in os.environ and os.environ.get(env) != '':
      command.append(arg)
      command.append(os.environ.get(env))
  if want_webui: # add this command directly before the "connect" subparser - otherwise you'll get silent crashes!
    command.append('-s')
    command.append(db_path)
  if len(listen_ip) > 1:
    command.append("connect")
    for i in range(1, len(listen_ip)):
      command.append("-n")
      command.append(listen_ip[i] + "," + listen_port)
    if dual := os.environ.get('DUALSTACK'):
      command.append("-d")
      command.append(dual)

  logger.debug("server_cmd: %s" % (" ".join(str(x) for x in command).strip()))
  pykms_process = subprocess.Popen(command)
  pykms_webui_process = None
  pykms_metrics_process = None

  try:
    # Start WebUI and/or metrics servers (always on separate ports)
    if want_webui or want_metrics:
      time.sleep(2) # Wait for the servers to start up

    if want_webui:
      pykms_webui_env = os.environ.copy()
      pykms_webui_env['PYKMS_SQLITE_DB_PATH'] = db_path
      pykms_webui_env['PORT'] = webui_port
      pykms_webui_env['PYKMS_LICENSE_PATH'] = '/LICENSE'
      pykms_webui_env['PYKMS_VERSION_PATH'] = '/VERSION'
      pykms_webui_process = subprocess.Popen(['gunicorn', '--log-level', os.environ.get('LOGLEVEL'), 'pykms_WebUI:app'], env=pykms_webui_env)

    if want_metrics:
      pykms_metrics_env = os.environ.copy()
      pykms_metrics_env['PYKMS_SQLITE_DB_PATH'] = db_path
      pykms_metrics_env['PORT'] = metrics_port
      pykms_metrics_process = subprocess.Popen(['gunicorn', '--log-level', os.environ.get('LOGLEVEL'), 'pykms_WebMetrics:app'], env=pykms_metrics_env)
  except Exception as e:
    logger.error("Failed to start webui/metrics (ignoring and continuing anyways): %s" % e)

  try:
    pykms_process.wait()
  except Exception:
    # In case of any error - just shut down
    pass
  except KeyboardInterrupt:
    pass
  logger.info("Shutting down...")

  if pykms_webui_process:
    logger.debug("Terminating webui process...")
    pykms_webui_process.terminate()
  if pykms_metrics_process:
    logger.debug("Terminating metrics process...")
    pykms_metrics_process.terminate()
  logger.debug("Terminating KMS process...")
  pykms_process.terminate()


# Main
if __name__ == "__main__":
  log_level_bootstrap = log_level = os.environ.get('LOGLEVEL', 'INFO')
  if log_level_bootstrap == "MININFO":
    log_level_bootstrap = "INFO"
  loggersrv = logging.getLogger('start.py')
  loggersrv.setLevel(log_level_bootstrap)
  streamhandler = logging.StreamHandler(sys.stdout)
  streamhandler.setLevel(log_level_bootstrap)
  formatter = logging.Formatter(fmt='\x1b[94m%(asctime)s %(levelname)-8s %(message)s', datefmt='%a, %d %b %Y %H:%M:%S')
  streamhandler.setFormatter(formatter)
  loggersrv.addHandler(streamhandler)
  loggersrv.info("Log level: %s" % log_level)
  loggersrv.debug("Running as UID/GID %s:%s" % (os.geteuid(), os.getegid()))

  start_kms(loggersrv)
