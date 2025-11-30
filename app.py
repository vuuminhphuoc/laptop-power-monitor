from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import psutil
import os
from collections import deque
from datetime import datetime

app = Flask(__name__, static_folder='static')
CORS(app)

# Battery history tracking (store last 10 readings)
battery_history = deque(maxlen=10)

def get_battery_health():
    """Get battery health information using powercfg battery report"""
    health_data = {
        'designCapacity': None,
        'fullChargeCapacity': None,
        'cycleCount': None,
        'batteryHealth': None,
        'batteryCondition': 'Unknown'
    }
    
    if os.name == 'nt':
        try:
            import subprocess
            import tempfile
            import re
            
            # Generate battery report
            report_path = os.path.join(tempfile.gettempdir(), 'battery-report.html')
            subprocess.run(['powercfg', '/batteryreport', '/output', report_path], 
                         capture_output=True, timeout=5)
            
            # Read and parse the report
            if os.path.exists(report_path):
                # Try with error handling for encoding issues
                try:
                    with open(report_path, 'r', encoding='utf-16-le') as f:
                        content = f.read()
                except UnicodeError:
                    # Fallback to utf-8 or ignore errors if utf-16 fails
                    with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                
                def extract_value(label, text):
                    """Helper to safely extract value from next td"""
                    pattern = r'' + label + r'.*?<td[^>]*>\s*(.*?)\s*</td>'
                    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                    if match:
                        return match.group(1).strip()
                    return None

                # Extract DESIGN CAPACITY
                design_raw = extract_value('DESIGN CAPACITY', content)
                if design_raw:
                    # Remove ' mWh', commas, and whitespace
                    clean_design = re.sub(r'[^0-9]', '', design_raw)
                    if clean_design:
                        health_data['designCapacity'] = int(clean_design)
                
                # Extract FULL CHARGE CAPACITY
                full_raw = extract_value('FULL CHARGE CAPACITY', content)
                if full_raw:
                    clean_full = re.sub(r'[^0-9]', '', full_raw)
                    if clean_full:
                        health_data['fullChargeCapacity'] = int(clean_full)
                
                # Extract CYCLE COUNT
                cycle_raw = extract_value('CYCLE COUNT', content)
                if cycle_raw:
                    clean_cycle = re.sub(r'[^0-9]', '', cycle_raw)
                    if clean_cycle:
                        health_data['cycleCount'] = int(clean_cycle)
                
                # Calculate battery health percentage
                if health_data['designCapacity'] and health_data['fullChargeCapacity']:
                    design = health_data['designCapacity']
                    full_charge = health_data['fullChargeCapacity']
                    if design > 0:
                        health_percentage = (full_charge / design) * 100
                        health_data['batteryHealth'] = round(health_percentage, 1)
                        
                        # Determine battery condition
                        if health_percentage >= 90:
                            health_data['batteryCondition'] = 'Excellent'
                        elif health_percentage >= 70:
                            health_data['batteryCondition'] = 'Good'
                        elif health_percentage >= 50:
                            health_data['batteryCondition'] = 'Fair'
                        elif health_percentage >= 30:
                            health_data['batteryCondition'] = 'Poor'
                        else:
                            health_data['batteryCondition'] = 'Replace Soon'
                
                # Clean up
                try:
                    os.remove(report_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"Error getting battery health from powercfg: {e}")
    
    return health_data

def detect_power_state(battery, history):
    """Detect detailed power state based on battery trends"""
    current_percent = battery.percent
    is_plugged = battery.power_plugged
    
    # Add current reading to history
    history.append({
        'percent': current_percent,
        'time': datetime.now(),
        'plugged': is_plugged
    })
    
    # Need at least 3 readings to detect trend
    if len(history) < 3:
        if is_plugged:
            return 'charging', '⚡ Charging...'
        else:
            return 'discharging', '🔋 On Battery'
    
    # Analyze trend
    recent = list(history)[-5:]  # Last 5 readings
    percent_changes = [recent[i]['percent'] - recent[i-1]['percent'] 
                       for i in range(1, len(recent))]
    avg_change = sum(percent_changes) / len(percent_changes) if percent_changes else 0
    
    if is_plugged:
        # Plugged in - detect state
        if current_percent >= 99:
            # Battery full
            if abs(avg_change) < 0.1:  # No change
                return 'ac_direct', '🔌 AC Direct (Battery Bypassed)'
            else:
                return 'trickle_charge', '🔌 AC Direct (Trickle Charge)'
        elif current_percent >= 75 and abs(avg_change) < 0.1:
            # Battery care mode (stops at 80-90%)
            return 'battery_care', '🛡️ Battery Care Mode (AC Direct)'
        elif avg_change > 0.05:
            # Battery increasing - charging
            return 'charging', '⚡ Charging (Using AC + Charging Battery)'
        elif avg_change < -0.05:
            # Battery decreasing while plugged - heavy load
            return 'heavy_load', '⚠️ Heavy Load (AC + Battery Drain)'
        else:
            # Stable while charging
            return 'charging_stable', '⚡ Charging (Maintaining Level)'
    else:
        # On battery
        if avg_change < -0.05:
            return 'discharging', '🔋 On Battery (Discharging)'
        else:
            return 'battery_stable', '🔋 On Battery (Stable)'

def get_power_status():
    """Get detailed power status information"""
    try:
        battery = psutil.sensors_battery()
        
        if battery is None:
            return {
                'error': 'Battery information not available',
                'hasBattery': False
            }
        
        # Calculate power consumption estimate
        # Note: Exact wattage requires WMI on Windows, this is an estimation
        power_consumption_watts = 0
        power_input_watts = 0
        
        # Try to get more detailed power info on Windows
        if os.name == 'nt':
            try:
                import wmi
                c = wmi.WMI()
                
                # Get battery info
                for battery_info in c.Win32_Battery():
                    design_capacity = getattr(battery_info, 'DesignCapacity', None)
                    estimated_charge = getattr(battery_info, 'EstimatedChargeRemaining', None)
                    
                    if design_capacity and estimated_charge:
                        # Rough estimation based on discharge rate
                        # This is approximate, actual values may vary
                        if battery.power_plugged:
                            # Charging - estimate charging power
                            power_input_watts = 65  # Typical laptop charger
                        else:
                            # On battery - estimate consumption from discharge rate
                            # Typical laptop: 15-45W depending on load
                            power_consumption_watts = 25  # Average estimation
            except ImportError:
                # WMI not available, use basic estimation
                if battery.power_plugged:
                    power_input_watts = 65  # Typical charger wattage
                else:
                    # Estimate based on battery percentage change
                    # Approximate consumption during discharge
                    power_consumption_watts = 25
            except Exception as e:
                print(f"WMI error: {e}")
                # Fallback to basic estimation
                if battery.power_plugged:
                    power_input_watts = 65
                else:
                    power_consumption_watts = 25
        else:
            # Non-Windows systems - basic estimation
            if battery.power_plugged:
                power_input_watts = 65
            else:
                power_consumption_watts = 25
        
        # Detect detailed power state
        power_state, power_state_text = detect_power_state(battery, battery_history)
        
        # Get battery health information
        battery_health = get_battery_health()
        
        # Determine if battery is being used
        battery_in_use = power_state in ['discharging', 'battery_stable', 'heavy_load']
        battery_charging = power_state in ['charging', 'charging_stable', 'trickle_charge']
        battery_bypassed = power_state in ['ac_direct', 'battery_care']
        
        # Calculate power flow
        if battery.power_plugged:
            if battery_bypassed:
                # AC Direct - no battery usage
                power_to_battery = 0
                power_to_system = power_input_watts
            elif battery_charging:
                # Charging - power split between system and battery
                power_to_battery = power_input_watts * 0.3  # ~30% to battery
                power_to_system = power_input_watts * 0.7   # ~70% to system
            elif power_state == 'heavy_load':
                # Heavy load - AC + battery both supplying
                power_to_battery = -15  # Battery draining
                power_to_system = power_input_watts + 15
            else:
                power_to_battery = 0
                power_to_system = power_input_watts
        else:
            # On battery
            power_to_battery = -power_consumption_watts
            power_to_system = power_consumption_watts
        
        # Calculate time remaining
        time_remaining = None
        if battery.secsleft != psutil.POWER_TIME_UNLIMITED and battery.secsleft != psutil.POWER_TIME_UNKNOWN:
            hours = battery.secsleft // 3600
            minutes = (battery.secsleft % 3600) // 60
            time_remaining = f"{hours}h {minutes}m"
        
        # Calculate voltage and amperage
        # Most laptop adapters: 19-20V (some are 5V for USB-C, 12V, 15V, or 19.5V)
        # We'll use typical values, ideally this would come from hardware sensors
        ac_voltage = 19.0  # Typical laptop adapter voltage
        battery_voltage = 11.1  # Typical 3-cell Li-ion battery (3.7V x 3)
        
        # Calculate current (A) from power (W) and voltage (V)
        # P = V × I, so I = P / V
        if battery.power_plugged and power_input_watts > 0:
            ac_current = round(power_input_watts / ac_voltage, 2)
        else:
            ac_current = 0
        
        if power_consumption_watts > 0:
            battery_current = round(power_consumption_watts / battery_voltage, 2)
        else:
            battery_current = 0
        
        return {
            'hasBattery': True,
            'batteryPercent': battery.percent,
            'powerPlugged': battery.power_plugged,
            'powerSource': 'AC Adapter' if battery.power_plugged else 'Battery',
            'powerInputWatts': power_input_watts if battery.power_plugged else 0,
            'powerConsumptionWatts': power_consumption_watts if not battery.power_plugged else power_input_watts * 0.8,
            'timeRemaining': time_remaining,
            'isCharging': battery.power_plugged,
            'status': 'Charging' if battery.power_plugged else 'Discharging',
            # Voltage and Current
            'voltage': ac_voltage if battery.power_plugged else battery_voltage,
            'current': ac_current if battery.power_plugged else battery_current,
            'acVoltage': ac_voltage,
            'acCurrent': ac_current,
            'batteryVoltage': battery_voltage,
            'batteryCurrent': battery_current,
            # New fields
            'powerState': power_state,
            'powerStateText': power_state_text,
            'batteryInUse': battery_in_use,
            'batteryCharging': battery_charging, 
            'batteryBypassed': battery_bypassed,
            'powerFlow': {
                'acInput': power_input_watts if battery.power_plugged else 0,
                'toBattery': round(power_to_battery, 1),
                'toSystem': round(power_to_system, 1),
                'fromBattery': round(-power_to_battery, 1) if power_to_battery < 0 else 0
            },
            # Battery Health
            'batteryHealth': battery_health
        }
    
    except Exception as e:
        return {
            'error': str(e),
            'hasBattery': False
        }

@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory('static', 'index.html')

@app.route('/api/power-status')
def power_status():
    """API endpoint for power status"""
    return jsonify(get_power_status())

if __name__ == '__main__':
    print("=" * 50)
    print("Laptop Power Monitor")
    print("=" * 50)
    print("Server running at: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
