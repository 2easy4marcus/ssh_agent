"""
USB Device diagnostics - based on tech lead's script.
Uses pyusb for proper device detection.
"""
try:
    import usb.core
    import usb.util
    USB_AVAILABLE = True
except ImportError:
    USB_AVAILABLE = False
    usb = None


def list_all_usb_devices() -> list[dict]:
    """List all connected USB devices with details."""
    if not USB_AVAILABLE:
        return []
    
    devices = usb.core.find(find_all=True)
    device_list = []
    
    for device in devices:
        try:
            manufacturer = usb.util.get_string(device, device.iManufacturer) or "Unknown"
            product = usb.util.get_string(device, device.iProduct) or "Unknown"
            serial = usb.util.get_string(device, device.iSerialNumber) or "N/A"
            
            device_info = {
                'bus': device.bus,
                'address': device.address,
                'vendor_id': hex(device.idVendor),
                'product_id': hex(device.idProduct),
                'manufacturer': manufacturer,
                'product': product,
                'serial': serial
            }
            device_list.append(device_info)
            usb.util.dispose_resources(device)
        except Exception:
            pass
    
    return device_list


def find_usb_device(vendor_id: str, product_id: str) -> tuple[bool, dict | None]:
    """Find a specific USB device by vendor/product ID."""
    if not USB_AVAILABLE:
        return False, None
    
    try:
        vid = int(vendor_id, 16) if isinstance(vendor_id, str) else vendor_id
        pid = int(product_id, 16) if isinstance(product_id, str) else product_id
    except ValueError:
        return False, None
    
    device = usb.core.find(idVendor=vid, idProduct=pid)
    
    if device is None:
        return False, None
    
    try:
        manufacturer = usb.util.get_string(device, device.iManufacturer) or "Unknown"
        product = usb.util.get_string(device, device.iProduct) or "Unknown"
        serial = usb.util.get_string(device, device.iSerialNumber) or "N/A"
        
        device_info = {
            'manufacturer': manufacturer,
            'product': product,
            'serial': serial,
            'bus': device.bus,
            'address': device.address,
            'vendor_id': hex(vid),
            'product_id': hex(pid)
        }
        
        try:
            device_info['kernel_driver_active'] = device.is_kernel_driver_active(0)
        except:
            device_info['kernel_driver_active'] = None
        
        usb.util.dispose_resources(device)
        return True, device_info
    except Exception:
        return True, {'vendor_id': hex(vid), 'product_id': hex(pid)}
