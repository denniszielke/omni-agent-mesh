
param location string = resourceGroup().location

resource subnetNSG 'Microsoft.Network/networkSecurityGroups@2022-01-01' = {
  name: 'nsg-${resourceGroup().name}'
  location: location
  properties: {
    securityRules: [
      {
        name: 'allow-http-apim-all'
        properties: {
          description: 'apim http allow rules'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '80'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 2000
          direction: 'Inbound'
          }      
      }
      {
        name: 'allow-https-apim-all'
        properties: {
          description: 'apim https allow rules'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 2001
          direction: 'Inbound'
          }      
      }
      {
        name: 'allow-6390-apim-all'
        properties: {
          description: 'apim 6390 allow rules'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '6390'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 2002
          direction: 'Inbound'
          }      
      }
      {
        name: 'allow-3443-apim-all'
        properties: {
          description: 'apim 3443 allow rules'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '3443'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 2003
          direction: 'Inbound'
          }      
      }
    ]
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2021-05-01' = {
  name: 'vnet-${resourceGroup().name}'
  location: resourceGroup().location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/19'
      ]
    }
    subnets: [
      {
        name: 'gateway'
        properties: {
          addressPrefix: '10.0.0.0/24'
          networkSecurityGroup: {
            id:  subnetNSG.id
          }
        }
      }
      {
        name: 'aca-apps'
        properties: {
          addressPrefix: '10.0.16.0/22'
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
          // delegations: [
          //   {
          //     name: 'Microsoft.App.testClients'
          //     properties: {
          //       serviceName: 'Microsoft.App/environments'
          //       actions: [
          //         'Microsoft.Network/virtualNetworks/subnets/join/action'
          //       ]
          //     }
          //   }
          // ]
        }
      }
    ]
  }
}
