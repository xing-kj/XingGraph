
# Example helm chart
Example Helm chart fro XingGraph with PostgreSQL and pgvector extension
It is not ready for production usage

## Prerequisites
Before deploying the Helm chart, ensure the following prerequisites are met: 

**Kubernetes Cluster**: A running Kubernetes cluster (e.g., Minikube, GKE, EKS).

**Helm**: Installed and configured for your Kubernetes cluster. You can install Helm by following the [official guide](https://helm.sh/docs/intro/install/). 

**kubectl**: Installed and configured to interact with your cluster. Follow the instructions [here](https://kubernetes.io/docs/tasks/tools/install-kubectl/).

Clone the Repository Clone this repository to your local machine and navigate to the directory.

## Example deploy Helm Chart:

   ```bash
   helm upgrade --install xinggraph deployment/helm \
  --namespace xinggraph --create-namespace \
  --set xinggraph.env.LLM_API_KEY="$YOUR_KEY"
   ```

**Uninstall Helm Release**:
   ```bash
   helm uninstall xinggraph
   ```

## Port forwarding
To access xinggraph, run
```
kubectl port-forward svc/xinggraph-service -n xinggraph 8000
```
it will be available at localhost:8000
