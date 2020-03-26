#!/usr/bin/env python

import sys, os
import argparse
from argparse import RawTextHelpFormatter
from configparser import ConfigParser
import psycopg2
import time
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY
import logging


LOG = logging.getLogger('dronedb-export')
logging.basicConfig(level=logging.INFO)

def setup_parser():
    parser = argparse.ArgumentParser(description='prometheus exporter for dronedb')
    parser.add_argument(
        '--host',
        dest='host',
        help='Drone database host',
        default=os.environ.get("DRONE_DATABASE_HOST", "localhost"))
    parser.add_argument(
        '--port',
        dest='dbport',
        help='Drone database port',
        default=os.environ.get("DRONE_DATABASE_PORT", "5432"))
    parser.add_argument(
        '--database',
        dest='database',
        help='Drone database',
        default=os.environ.get("DRONE_DATABASE"))
    parser.add_argument(
        '-u', '--username',
        dest='username',
        help='Drone database user',
        default=os.environ.get("DRONE_DATABASE_USER"))
    parser.add_argument(
        '-p', '--password',
        dest='password',
        help='Drone database password',
        default=os.environ.get("DRONE_DATABASE_PASSWORD"))
    parser.add_argument(
        '--listen-port',
        dest='listen_port',
        help='prometheus exporter listen port',
        default=os.environ.get("DRONE_LISTEN_PORT", "9698"))
    return parser.parse_args()

#def config(section):
#    filename='config.ini'
#    # create a parser
#    parser = ConfigParser()
#    # read config file
#    parser.read(filename)
# 
#    # get section, default to postgresql
#    db = {}
#    try:
#        if parser.has_section(section):
#            params = parser.items(section)
#            for param in params:
#                db[param[0]] = param[1]
#        else:
#            raise Exception('Section {0} not found in the {1} file'.format(section, filename))
#    except Exception as e:
#        LOG.error(e)
#        sys.exit(os.EX_CONFIG)
# 
#    return(db)


class DB:
    
    def __init__(self, host, port, dbname, user, password):
        try:
            self.conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
            self.cur = self.conn.cursor()
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    def execute_all(self, query):
        self.cur.execute(query)
        try:
            self.cur.execute(query)
            response = self.cur.fetchall()
        except:
            response = 'Query failed'
        return(response)

    def execute_one(self, query):
        self.cur.execute(query)
        try:
            self.cur.execute(query)
            response = self.cur.fetchone()
        except:
            response = 'Query failed'
        return(response)

    def close_db(self):
        self.cur.close()
        self.conn.close()


class DroneCollector(object):


    def __init__(self, host, port, database, user, password):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.data = {}
        self.db_up = True


    def _collect_repos(self):
        results = self.drone.execute_all("select repo_name,repo_id from repos where repo_active = 't';")

        for repo in results:
            self.data[repo[0]] = { "id": repo[1]}


    def _collect_last_successful_build(self):
        for repo in self.data:
            query = "select build_number from builds where build_repo_id = " + str(self.data[repo]['id']) + " and build_status = 'success' order by build_number DESC limit 1;"
            results = self.drone.execute_one(query)
            if results:
                self.data[repo].update(lastSuccessfulBuildId = results[0])


    def _collect_last_build(self):
        for repo in self.data:
            query = "select build_number from builds where build_repo_id = " + str(self.data[repo]['id']) + " order by build_number DESC limit 1;"
            results = self.drone.execute_one(query)
            if results:
                self.data[repo].update(lastBuildId = results[0])


    def _collect_last_successful_build_time(self):
        for repo in self.data:
            query = "select build_finished - build_started from builds where build_repo_id = " + str(self.data[repo]['id']) + " and build_status = 'success' order by build_number DESC limit 1;"
            results = self.drone.execute_one(query)
            if results:
                self.data[repo].update(lastSuccessfulBuildTime = results[0])


    def _collect_last_build_time(self):
        for repo in self.data:
            query = "select build_finished - build_started from builds where build_repo_id = " + str(self.data[repo]['id']) + " order by build_number DESC limit 1;"
            results = self.drone.execute_one(query)
            if results:
                self.data[repo].update(lastBuildTime = results[0])


    def collect(self):
        self.drone = DB(self.host, self.port, self.database, self.user, self.password)
        self._collect_repos()
        self._collect_last_successful_build()
        self._collect_last_build()
        self._collect_last_successful_build_time()
        self._collect_last_build_time()

        for repo in self.data:
            if 'lastSuccessfulBuildTime' in self.data[repo]:
                lsbt = GaugeMetricFamily(
                    'dronedb_repo_last_successful_build_time',
                    'Last successful build time in seconds',
                    labels=["repo"])
                lsbt.add_metric(
                    [repo],
                    str(self.data[repo]['lastSuccessfulBuildTime']))
                yield(lsbt)

            if 'lastBuildTime' in self.data[repo]:
                lbt = GaugeMetricFamily(
                    'dronedb_repo_last_build_time',
                    'Last build time in seconds',
                    labels=["repo"])
                lbt.add_metric(
                    [repo],
                    str(self.data[repo]['lastBuildTime']))
                yield(lbt)

            if 'lastSuccessfulBuildId' in self.data[repo]:
                lsbi = CounterMetricFamily(
                    'dronedb_repo_last_successful_build_id',
                    'Last successful build id',
                    labels=["repo"])
                lsbi.add_metric(
                    [repo],
                    str(self.data[repo]['lastSuccessfulBuildId']))
                yield(lsbi)

            if 'lastBuildId' in self.data[repo]:
                lbi = CounterMetricFamily(
                    'dronedb_repo_last_build_id',
                    'Last build id',
                    labels=["repo"])
                lbi.add_metric(
                    [repo],
                    str(self.data[repo]['lastBuildId']))
                yield(lbi)
        
        self.drone.close_db()
        return(self.data)

if __name__ == "__main__":
    args = setup_parser()
    LOG.info('Starting dronedb exporter on http://localhost:%s' % args.listen_port)
    REGISTRY.register(DroneCollector(args.host, args.dbport, args.database, args.username, args.password))
    start_http_server(int(args.listen_port))
    while True:
        time.sleep(1)

