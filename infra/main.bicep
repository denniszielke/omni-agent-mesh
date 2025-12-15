targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
@allowed(['northcentralus','swedencentral', 'eastus2', 'westus3'])
param location string

param resourceGroupName string = ''
param containerAppsEnvironmentName string = ''
param containerRegistryName string = ''
param openaiName string = ''
param applicationInsightsDashboardName string = ''
param applicationInsightsName string = ''
param logAnalyticsName string = ''
param aiSearchIndexName string = 'queries-index'

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

param smallCompletionDeploymentModelName string = 'gpt-4.1-mini'
param smallCompletionModelName string = 'gpt-4.1-mini'
param smallCompletionModelVersion string = '2025-04-14'

param bigCompletionDeploymentModelName string = 'gpt-5-nano'
param bigCompletionModelName string = 'gpt-5-nano'
param bigCompletionModelVersion string = '2025-08-07'

param embeddingDeploymentModelName string = 'text-embedding-3-small'
param embeddingModelName string = 'text-embedding-3-small'
param openaiApiVersion string = '2024-10-21'
param openaiCapacity int = 30
param modelDeployments array = [
  {
    name: smallCompletionDeploymentModelName
    sku: 'GlobalStandard'
    model: {
      format: 'OpenAI'
      name: smallCompletionModelName
      version: smallCompletionModelVersion
    }
  }
  {
    name: bigCompletionDeploymentModelName
    sku: 'GlobalStandard'
    model: {
      format: 'OpenAI'
      name: bigCompletionModelName
      version: bigCompletionModelVersion
    }
  }
  {
    name: embeddingDeploymentModelName
    sku: 'GlobalStandard'
    model: {
      format: 'OpenAI'
      name: embeddingModelName
      version: '1'
    }
  }
]

// Organize resources in a resource group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

module vnet './core/host/vnet.bicep' = {
  name: 'vnet'
  scope: resourceGroup
  params: {
    location: location
  }
}

// Container apps host (including container registry)
module containerApps './core/host/container-apps.bicep' = {
  name: 'container-apps'
  scope: resourceGroup
  params: {
    name: 'app'
    containerAppsEnvironmentName: !empty(containerAppsEnvironmentName) ? containerAppsEnvironmentName : '${abbrs.appManagedEnvironments}${resourceToken}'
    containerRegistryName: !empty(containerRegistryName) ? containerRegistryName : '${abbrs.containerRegistryRegistries}${resourceToken}'
    location: location
    logAnalyticsWorkspaceName: monitoring.outputs.logAnalyticsWorkspaceName
  }
}

// Azure OpenAI Model
module openai './ai/openai.bicep' = {
  name: 'openai'
  scope: resourceGroup
  params: {
    location: location
    tags: tags
    customDomainName: !empty(openaiName) ? openaiName : '${abbrs.cognitiveServicesAccounts}${resourceToken}'
    name: !empty(openaiName) ? openaiName : '${abbrs.cognitiveServicesAccounts}${resourceToken}'
    deployments: modelDeployments
    capacity: openaiCapacity
  }
}

// Azure AI Search
module search './ai/search.bicep' = {
  name: 'search'
  scope: resourceGroup
  params: {
    location: location
    tags: tags
    name: !empty(openaiName) ? openaiName : '${abbrs.searchSearchServices}${resourceToken}'
  }
}

// Monitor application with Azure Monitor
module monitoring './core/monitor/monitoring.bicep' = {
  name: 'monitoring'
  scope: resourceGroup
  params: {
    location: location
    tags: tags
    logAnalyticsName: !empty(logAnalyticsName) ? logAnalyticsName : '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    applicationInsightsName: !empty(applicationInsightsName) ? applicationInsightsName : '${abbrs.insightsComponents}${resourceToken}'
    applicationInsightsDashboardName: !empty(applicationInsightsDashboardName) ? applicationInsightsDashboardName : '${abbrs.portalDashboards}${resourceToken}'
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = resourceGroup.name

output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.applicationInsightsConnectionString
output APPLICATIONINSIGHTS_NAME string = monitoring.outputs.applicationInsightsName
output AZURE_CONTAINER_ENVIRONMENT_NAME string = containerApps.outputs.environmentName
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerApps.outputs.registryLoginServer
output AZURE_CONTAINER_REGISTRY_NAME string = containerApps.outputs.registryName
output OPENAI_API_TYPE string = 'azure'
output AZURE_OPENAI_VERSION string = openaiApiVersion
output AZURE_OPENAI_API_KEY string = openai.outputs.openaiKey
output AZURE_OPENAI_ENDPOINT string = openai.outputs.openaiEndpoint
output AZURE_OPENAI_SMALL_CHAT_MODEL string = smallCompletionModelName
output AZURE_OPENAI_SMALL_CHAT_DEPLOYMENT_NAME string = smallCompletionDeploymentModelName
output AZURE_OPENAI_BIG_CHAT_MODEL string = bigCompletionModelName
output AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME string = bigCompletionDeploymentModelName
output AZURE_OPENAI_EMBEDDING_MODEL string = embeddingModelName
output AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME string = embeddingDeploymentModelName
output DEFAULT_DOMAIN string = containerApps.outputs.defaultDomain
output AZURE_AI_SEARCH_NAME string = search.outputs.searchName
output AZURE_AI_SEARCH_ENDPOINT string = search.outputs.searchEndpoint
output AZURE_AI_SEARCH_KEY string = search.outputs.searchAdminKey
output AZURE_AI_SEARCH_INDEX_NAME string = aiSearchIndexName
output AZURE_OPENAI_EMBEDDING_DIMENSIONS string = '1536'
output AZURE_OPENAI_API_VERSION string = openaiApiVersion
output INTRANET_MCP_SERVER_URL string = 'https://mcp-05-intranet-server.${containerApps.outputs.defaultDomain}/mcp'
output POLICY_MCP_SERVER_URL string = 'https://mcp-06-policy-server.${containerApps.outputs.defaultDomain}/mcp'
