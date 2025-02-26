#!/bin/bash

# Apply all Kubernetes YAML files
kubectl apply -f ZookeeperDeployment.yml
kubectl apply -f KafkaDeployment.yml
kubectl apply -f MongoDBDeployment.yml
kubectl apply -f CrudServiceDeployment.yml
kubectl apply -f gRPCServiceDeployment.yml
kubectl apply -f gRPCClientDeployment.yml
kubectl apply -f KafkaConsumerDeployment.yml
kubectl apply -f prometheus-deployment.yml
kubectl apply -f GrafanaDeployment.yml
kubectl apply -f HPAforCRUDService.yml