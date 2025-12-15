#!/bin/bash

set -e

APP_NAME="$1"

if [ "$APP_NAME" == "" ]; then
echo "No app  name provided - aborting"
exit 0;
fi

AZURE_ENV_NAME="$2"

if [ "$AZURE_ENV_NAME" == "" ]; then
echo "No environment name provided - aborting"
exit 0;
fi


if [[ $APP_NAME =~ ^[a-z0-9/_-]{5,15}$ ]]; then
    echo "app name $APP_NAME is valid"
else
    echo "app name $APP_NAME  is invalid - only numbers and lower case min 5 and max 12 characters allowed - aborting"
    exit 0;
fi

RESOURCE_GROUP="rg-$AZURE_ENV_NAME"

if [ $(az group exists --name $RESOURCE_GROUP) = false ]; then
    echo "resource group $RESOURCE_GROUP does not exist"
    error=1
else   
    echo "resource group $RESOURCE_GROUP already exists"
    LOCATION=$(az group show -n $RESOURCE_GROUP --query location -o tsv)
fi

APPINSIGHTS_NAME=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.Insights/components" --query "[0].name" -o tsv)
AZURE_CONTAINER_REGISTRY_NAME=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.ContainerRegistry/registries" --query "[0].name" -o tsv)
OPENAI_NAME=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.CognitiveServices/accounts" --query "[0].name" -o tsv)
ENVIRONMENT_NAME=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.App/managedEnvironments" --query "[0].name" -o tsv)
IDENTITY_NAME=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.ManagedIdentity/userAssignedIdentities" --query "[0].name" -o tsv)
SEARCH_NAME=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.Search/searchServices" --query "[0].name" -o tsv)
SERVICE_NAME=$APP_NAME
AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)

AZURE_AI_SEARCH_INDEX_NAME="hr-policies-index"
AZURE_OPENAI_SMALL_CHAT_MODEL="gpt-4.1-mini"
AZURE_OPENAI_SMALL_CHAT_DEPLOYMENT_NAME="gpt-4.1-mini"
AZURE_OPENAI_BIG_CHAT_MODEL="gpt-5-mini"
AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME="gpt-5-mini"
AZURE_OPENAI_VERSION="2024-10-21"
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME="text-embedding-3-small"
AZURE_OPENAI_EMBEDDING_MODEL="text-embedding-3-small"

echo "container registry name: $AZURE_CONTAINER_REGISTRY_NAME"
echo "application insights name: $APPINSIGHTS_NAME"
echo "openai name: $OPENAI_NAME"
echo "environment name: $ENVIRONMENT_NAME"
echo "identity name: $IDENTITY_NAME"
echo "service name: $SERVICE_NAME"
echo "search name: $SEARCH_NAME"

CONTAINER_APP_EXISTS=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.App/containerApps" --query "[?contains(name, '$SERVICE_NAME')].id" -o tsv)
EXISTS="false"

if [ "$CONTAINER_APP_EXISTS" == "" ]; then
    echo "container app $SERVICE_NAME does not exist"
else
    echo "container app $SERVICE_NAME already exists"
    EXISTS="true"
fi

IMAGE_TAG=$(date '+%m%d%H%M%S')

az acr build --subscription ${AZURE_SUBSCRIPTION_ID} --registry ${AZURE_CONTAINER_REGISTRY_NAME} \
    --image $SERVICE_NAME:$IMAGE_TAG \
    --file ./Dockerfile.workflow .
IMAGE_NAME="${AZURE_CONTAINER_REGISTRY_NAME}.azurecr.io/$SERVICE_NAME:$IMAGE_TAG"

echo "deploying image: $IMAGE_NAME"

SERVICE_NAME="${APP_NAME//_/-}"

az deployment group create -g $RESOURCE_GROUP -f ./infra/app/frontend.bicep \
          -p name=$SERVICE_NAME -p location=$LOCATION -p containerAppsEnvironmentName=$ENVIRONMENT_NAME \
          -p containerRegistryName=$AZURE_CONTAINER_REGISTRY_NAME -p applicationInsightsName=$APPINSIGHTS_NAME \
          -p openaiName=$OPENAI_NAME -p openaiEndpoint="https://$OPENAI_NAME.openai.azure.com" \
          -p smallCompletionDeploymentName=$AZURE_OPENAI_SMALL_CHAT_DEPLOYMENT_NAME \
          -p bigCompletionDeploymentName=$AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME \
          -p embeddingDeploymentModelName=$AZURE_OPENAI_EMBEDDING_MODEL \
          -p searchIndexName=$AZURE_AI_SEARCH_INDEX_NAME \
          -p openaiApiVersion=$AZURE_OPENAI_VERSION \
          -p searchName=$SEARCH_NAME -p searchEndpoint="https://$SEARCH_NAME.search.windows.net" \
          -p identityName=$IDENTITY_NAME -p imageName=$IMAGE_NAME -p exists=$EXISTS --query properties.outputs