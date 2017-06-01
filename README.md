# Activity

A web service providing an easy way to train and generate JavaScript-based machine learning classifiers.
## Set up

Start Docker containers with
```bash
docker-compose -p activity up -d
```

Download training data
```bash
git clone git@github.com:teco-kit/CSS-RTutorial.git data
```

Install requirements.txt
```bash
pip install -r requirements.txt
```

Convert training data from ARFF to InfluxDB line protocol
```bash
python activity/arff-to-influxdb.py -i data -o data.txt -m devicemotion
```

Create database and store training data to InfluxDB
```bash
curl -i -XPOST 'http://localhost:8086/query' --data-urlencode 'q=CREATE DATABASE activity'
curl -i -XPOST 'http://localhost:8086/write?db=activity' --data-binary @data.txt
```

