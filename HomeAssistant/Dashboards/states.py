import requests
import json
import yaml
from datetime import datetime
from collections import defaultdict

class HomeAssistantAPI:
    def __init__(self, url, token):
        self.url = url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def get_states(self):
        response = requests.get(f"{self.url}/api/states", headers=self.headers)
        return response.json()
    
    def get_entity(self, entity_id):
        response = requests.get(f"{self.url}/api/states/{entity_id}", headers=self.headers)
        return response.json()
    
    def get_config(self):
        """Get Home Assistant configuration info"""
        try:
            response = requests.get(f"{self.url}/api/config", headers=self.headers)
            return response.json()
        except:
            return {}

def organize_entities_for_dashboard(entities, config=None):
    """Organize entities by domain and area for dashboard creation"""
    
    # Group entities by domain (light, sensor, switch, etc.)
    domains = defaultdict(list)
    
    # Group entities by area
    areas = defaultdict(list)
    
    # Track available attributes for each domain
    domain_attributes = defaultdict(set)
    
    dashboard_data = {
        'export_info': {
            'timestamp': datetime.now().isoformat(),
            'total_entities': len(entities),
            'ha_config': config or {}
        },
        'domains': {},
        'areas': {},
        'entities': {},
        'dashboard_suggestions': {
            'recommended_cards': [],
            'domain_recommendations': {},
            'area_recommendations': {}
        }
    }
    
    for entity in entities:
        entity_id = entity['entity_id']
        domain = entity_id.split('.')[0]
        state = entity['state']
        attributes = entity.get('attributes', {})
        
        # Get area information - improved logic
        friendly_name = attributes.get('friendly_name', '')
        area = (
            attributes.get('area_id') or 
            attributes.get('area') or
            # Extract from friendly name more intelligently
            (friendly_name.split(' - ')[0] if ' - ' in friendly_name else None) or
            # Extract from entity_id prefix
            entity_id.split('.')[0].replace('_', ' ').title() or
            'Unassigned'
        )
        
        # Collect entity info
        entity_info = {
            'entity_id': entity_id,
            'state': state,
            'friendly_name': attributes.get('friendly_name', entity_id),
            'unit_of_measurement': attributes.get('unit_of_measurement'),
            'device_class': attributes.get('device_class'),
            'icon': attributes.get('icon'),
            'area': area,
            'domain': domain,
            'last_changed': entity.get('last_changed'),
            'last_updated': entity.get('last_updated'),
            'attributes': attributes
        }
        
        # Add to domains
        domains[domain].append(entity_info)
        
        # Add to areas
        areas[area].append(entity_info)
        
        # Track attributes for this domain
        domain_attributes[domain].update(attributes.keys())
        
        # Store in main entities dict
        dashboard_data['entities'][entity_id] = entity_info
    
    # Process domains with dashboard recommendations
    for domain, domain_entities in domains.items():
        dashboard_data['domains'][domain] = {
            'count': len(domain_entities),
            'entities': domain_entities,
            'common_attributes': list(domain_attributes[domain]),
            'suggested_cards': get_domain_card_suggestions(domain, domain_entities)
        }
    
    # Process areas
    for area, area_entities in areas.items():
        dashboard_data['areas'][area] = {
            'count': len(area_entities),
            'entities': area_entities,
            'domains_in_area': list(set(e['domain'] for e in area_entities)),
            'suggested_layout': get_area_layout_suggestions(area, area_entities)
        }
    
    # Generate overall dashboard suggestions
    dashboard_data['dashboard_suggestions'] = generate_dashboard_suggestions(domains, areas)
    
    return dashboard_data

def get_domain_card_suggestions(domain, entities):
    """Suggest appropriate Lovelace cards for each domain"""
    suggestions = []
    
    card_mappings = {
        'light': ['light', 'entities', 'mushroom-light-card'],
        'switch': ['entities', 'button', 'mushroom-entity-card'],
        'sensor': ['sensor', 'gauge', 'graph', 'mushroom-entity-card'],
        'binary_sensor': ['entities', 'mushroom-entity-card'],
        'climate': ['thermostat', 'mushroom-climate-card'],
        'cover': ['entities', 'mushroom-cover-card'],
        'media_player': ['media-control', 'mushroom-media-player-card'],
        'camera': ['picture-entity', 'picture-glance'],
        'person': ['entity', 'mushroom-person-card'],
        'device_tracker': ['entity', 'map'],
        'weather': ['weather-forecast', 'mushroom-weather-card'],
        'vacuum': ['vacuum', 'mushroom-vacuum-card'],
        'alarm_control_panel': ['alarm-panel', 'mushroom-alarm-control-panel-card'],
        'lock': ['entities', 'mushroom-lock-card'],
        'fan': ['entities', 'mushroom-fan-card']
    }
    
    return card_mappings.get(domain, ['entities', 'mushroom-entity-card'])

def get_area_layout_suggestions(area, entities):
    """Suggest layout for area-based dashboards"""
    domains_in_area = set(e['domain'] for e in entities)
    
    layout = {
        'suggested_sections': [],
        'card_count_estimate': len(entities),
        'layout_type': 'grid' if len(entities) > 10 else 'vertical-stack'
    }
    
    # Suggest sections based on domains present
    if 'light' in domains_in_area:
        layout['suggested_sections'].append('Lighting Controls')
    if 'climate' in domains_in_area:
        layout['suggested_sections'].append('Climate Control')
    if any(d in domains_in_area for d in ['sensor', 'binary_sensor']):
        layout['suggested_sections'].append('Sensors & Monitoring')
    if 'media_player' in domains_in_area:
        layout['suggested_sections'].append('Media & Entertainment')
    if any(d in domains_in_area for d in ['switch', 'cover', 'lock']):
        layout['suggested_sections'].append('Device Controls')
    
    return layout

def generate_dashboard_suggestions(domains, areas):
    """Generate comprehensive dashboard creation suggestions"""
    
    suggestions = {
        'recommended_dashboards': [],
        'popular_card_types': [],
        'integration_requirements': [],
        'hacs_components': []
    }
    
    # Suggest dashboard types based on available domains
    if 'light' in domains and len(domains['light']) > 5:
        suggestions['recommended_dashboards'].append('Lighting Control Dashboard')
    
    if 'sensor' in domains and len(domains['sensor']) > 10:
        suggestions['recommended_dashboards'].append('Monitoring Dashboard')
    
    if 'climate' in domains or 'weather' in domains:
        suggestions['recommended_dashboards'].append('Climate & Weather Dashboard')
    
    if 'media_player' in domains:
        suggestions['recommended_dashboards'].append('Entertainment Dashboard')
    
    if 'camera' in domains or 'alarm_control_panel' in domains:
        suggestions['recommended_dashboards'].append('Security Dashboard')
    
    # Suggest popular HACS components based on entities
    hacs_suggestions = [
        'mushroom-cards',  # Modern UI cards
        'card-mod',        # Custom styling
        'layout-card',     # Advanced layouts
        'auto-entities',   # Dynamic entity lists
        'button-card',     # Customizable buttons
        'mini-graph-card', # Compact graphs
        'weather-card',    # Enhanced weather
        'vacuum-card'      # Vacuum controls
    ]
    
    if 'light' in domains and len(domains['light']) > 3:
        hacs_suggestions.append('light-entity-card')
    
    if 'sensor' in domains and len(domains['sensor']) > 5:
        hacs_suggestions.extend(['mini-graph-card', 'bar-card', 'gauge-card'])
    
    if 'camera' in domains:
        hacs_suggestions.extend(['frigate-hass-card', 'camera-dashboard-card'])
    
    suggestions['hacs_components'] = list(set(hacs_suggestions))
    
    return suggestions

# Main execution
if __name__ == "__main__":
    # Your Home Assistant connection
    ha = HomeAssistantAPI("http://172.20.0.40:8123", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhZTE5MGJhMDM4N2I0ZjA5YTA2N2Q4ZWFjNDZjYTkxMCIsImlhdCI6MTc1ODQzMjA1MiwiZXhwIjoyMDczNzkyMDUyfQ.nsKvSpihEOJpK_dbDiu4XYBVnpqqvXjrJO5R0tAYhO8")
    
    print("🔄 Fetching Home Assistant states...")
    entities = ha.get_states()
    
    print("🔄 Getting HA configuration...")
    config = ha.get_config()
    
    print(f"✅ Found {len(entities)} entities")
    print("🔄 Organizing data for dashboard creation...")
    
    # Organize data for dashboard creation
    dashboard_data = organize_entities_for_dashboard(entities, config)
    
    # Export to YAML file
    print("🔄 Exporting to states.yml...")
    with open('states.yml', 'w') as file:
        yaml.dump(dashboard_data, file, default_flow_style=False, sort_keys=False, indent=2)
    
    print("✅ Export complete! states.yml created")
    
    # Print summary
    print(f"""
📊 Export Summary:
   • Total Entities: {len(entities)}
   • Domains Found: {len(dashboard_data['domains'])}
   • Areas Identified: {len(dashboard_data['areas'])}
   • Recommended Dashboards: {len(dashboard_data['dashboard_suggestions']['recommended_dashboards'])}
   
🎨 Top Domains:
""")
    
    # Show top domains by entity count
    sorted_domains = sorted(dashboard_data['domains'].items(), 
                          key=lambda x: x[1]['count'], reverse=True)
    
    for domain, info in sorted_domains[:10]:
        print(f"   • {domain}: {info['count']} entities")
    
    print(f"""
🏠 Areas Found:
""")
    
    # Show areas by entity count
    sorted_areas = sorted(dashboard_data['areas'].items(), 
                         key=lambda x: x[1]['count'], reverse=True)
    
    for area, info in sorted_areas[:10]:
        print(f"   • {area}: {info['count']} entities")
    
    print(f"""
💡 Recommended HACS Components:
   • {', '.join(dashboard_data['dashboard_suggestions']['hacs_components'][:5])}
   
📁 File created: states.yml
   This file contains all entity data organized for dashboard creation!
""")