import requests
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, String, Integer, DateTime
from datetime import datetime, timezone, MINYEAR
import json
import time
import os

basedir = os.path.abspath(os.path.dirname(__file__))

rancher_ip = os.environ.get("RANCHER_IP") or "10.62.164.163"
admin_token = os.environ.get("ADMIN_TOKEN") or "token-p5lzr:fj8w4h84xvv44tqz47x2bchc9r7zwqxljk99mks7xbk9b2pz9tktkx"
admin_token = "Bearer " + admin_token
default_time = datetime(year=MINYEAR, month=1, day=1, tzinfo=timezone.utc)
default_time_1 = datetime(year=MINYEAR, month=2, day=1, tzinfo=timezone.utc)

mysql_info = os.environ.get("MYSQL_INFO") or 'mysql+pymysql://root:zuultest@172.17.0.1/rancher_logging'
engine = create_engine(mysql_info)
Session = sessionmaker(bind=engine)
Base = declarative_base()

requests.packages.urllib3.disable_warnings()

wait_interval = os.environ.get("WAIT_INTERVAL") or "60"
wait_interval = int(wait_interval)


class Node(Base):
    __tablename__ = "nodes"
    id = Column(Integer, primary_key=True)
    hostname = Column(String(64))
    node_id = Column(String(64))
    cluster_id = Column(String(64))
    start_time = Column(DateTime, default=default_time)
    stop_time = Column(DateTime, default=default_time)

    def __init__(self, hostname=None, node_id=None, cluster_id=None, start_time=default_time, stop_time=default_time):
        self.hostname = hostname
        self.node_id = node_id
        self.cluster_id = cluster_id
        self.start_time = start_time


def update_db():    
    # 1. obtain node data from rancher
    # 2. obtain data from database with stop_time is min. Compare with 1 and update.
    # 3. Go through node from rancher, check if entry state is active, and if data is in database.
    #    If active and not in database, add to database.

    # request rancher data
    url = "https://{0}/v3/nodes".format(rancher_ip)
    querystring = {}
    payload = {}
    headers = {
        'Authorization': admin_token,
        'Content-Type': "application/json"
    }
    try:
        response = requests.get(
            url, data=json.dumps(payload), headers=headers, params=querystring,
            verify=False)
    except:
        res = datetime.now(timezone.utc).isoformat(timespec="seconds")
        res += " cannot connect to rancher server 500"
        print(res)
        return

    response_json = json.loads(response.text)
    if response.status_code != 200:
        res = datetime.now(timezone.utc).isoformat(timespec="seconds") + " "
        res += str(response.status_code) + " rancher response: "
        res += response_json["message"]
        print(res)
        return

    session = Session()

    active_node_list = session.query(Node).filter(Node.stop_time<default_time_1).all()
    for db_node in active_node_list:
        id_found = False
        for datum in response_json["data"]:
            if db_node.node_id == datum["id"]:
                id_found = True
                break
        if not id_found:
            session.query(Node).filter(Node.id==db_node.id).update({"stop_time": datetime.now(timezone.utc)})

    for datum in response_json["data"]:
        if datum["state"] == "active":
            node_count = session.query(Node).filter(Node.node_id==datum["id"]).count()
            if node_count == 0:
                node_entry = Node(
                    hostname=datum["requestedHostname"],
                    node_id=datum["id"],
                    cluster_id=datum["clusterId"],
                    start_time=datetime.now(timezone.utc))
                session.add(node_entry)

    session.commit()
    session.close()
    res = datetime.now(timezone.utc).isoformat(timespec="seconds") + " db updated."
    print(res)


def main():

    Base.metadata.create_all(engine)
    while True:
        update_db()
        time.sleep(wait_interval)


if __name__ == "__main__":
    main()

