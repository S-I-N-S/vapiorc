# vapiorc - VM Orchestrator

A minimal, abstract VM orchestrator for containerized Windows VMs using dockurr/windows Docker images.

## Features

- **Golden Image Management**: Create base Windows installations once and reuse them
- **Hot Spare Pool**: Pre-warmed VMs ready for immediate assignment
- **Simple REST API**: Easy integration with any project
- **Automatic VM Lifecycle**: Handles creation, assignment, and cleanup
- **Docker-based**: Everything runs in containers

## Quick Start

1. **Prerequisites**:
   - Docker with KVM support
   - Docker Compose
   - Linux host with /dev/kvm and /dev/net/tun

2. **Start the system**:
   ```bash
   docker-compose up -d
   ```

3. **Create a golden image**:
   ```bash
   curl -X POST http://localhost:8000/api/vms/golden-images?vm_type=11
   ```

4. **Monitor the installation** (via noVNC at the assigned port), then mark it ready:
   ```bash
   curl -X POST http://localhost:8000/api/vms/golden-images/{golden_id}/ready
   ```

5. **Assign a VM to a task**:
   ```bash
   curl -X POST "http://localhost:8000/api/vms/assign?assigned_to=my_task_id"
   ```

## API Endpoints

### Golden Images
- `POST /api/vms/golden-images` - Create a new golden image
- `POST /api/vms/golden-images/{id}/ready` - Mark golden image as ready

### VM Management
- `GET /api/vms/instances` - List all VM instances
- `POST /api/vms/instances` - Create a new VM instance
- `POST /api/vms/assign` - Assign a VM from hot spare pool
- `POST /api/vms/instances/{id}/release` - Release VM (destroys for security)
- `DELETE /api/vms/instances/{id}` - Destroy a VM instance

### Maintenance
- `POST /api/vms/hot-spares/ensure` - Manually trigger hot spare replenishment
- `GET /health` - Health check

## Configuration

Environment variables:

- `VAPIORC_STORAGE_PATH`: Storage path for VM data (default: `/tmp/vapiorc`)
- `VAPIORC_NETWORK`: Docker network name (default: `vapiorc_default`)
- `VAPIORC_PORT_START/END`: Port range for VMs (default: 8001-8100)
- `VAPIORC_HOT_SPARES`: Number of hot spares to maintain (default: 2)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string

## Integration Example

```python
import requests

# Assign a VM
response = requests.post("http://localhost:8000/api/vms/assign?assigned_to=task_123")
vm_info = response.json()

# Use the VM (noVNC web interface)
novnc_url = vm_info["novnc_url"]
rdp_port = vm_info["rdp_port"]

# Your automation code here...

# Release when done (VM will be destroyed for security)
requests.post(f"http://localhost:8000/api/vms/instances/{vm_info['instance_id']}/release")
```

## Architecture

- **FastAPI** app with REST endpoints
- **PostgreSQL** for VM instance tracking
- **Redis** for caching and queuing
- **Docker** containers for VM instances using dockurr/windows
- **Hot Spare Pool** maintains ready-to-use VMs
- **Golden Image System** for fast VM provisioning

## Security & Notes

- **Security-First Design**: VMs are completely destroyed when released (no data persistence between tasks)
- **Hot Spare Replenishment**: New hot spares are automatically created after VMs are destroyed
- First golden image creation takes ~20-30 minutes for Windows installation
- Subsequent VM creation from golden image takes ~2-3 minutes
- Hot spares reduce assignment time to seconds
- Each VM gets a unique noVNC port for web access
- RDP access available on port+1000
- Windows version: Uses Windows 11 (VERSION=11)

## License

Open source - integrate into any project.


Currently need to get the 'true' files paths working as we were mapping the oem and storage folders to paths inside the python container and not the actual host path. Need to test to see if we fixed those path mappings and that the install.bat works and that the copying of files works