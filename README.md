# 💊 Caduceus Multi-Tenancy Pharmacy System (Cloud-Hosted)

Welcome to the **Caduceus Pharmacy OS** ecosystem. This repository contains a production-ready, cloud-hosted, multi-tenant pharmacy management platform designed to streamline operations across multiple pharmacies, branches, and warehouses.

The system handles core pharmacy workflows including **inventory tracking, multi-branch procurement, digital prescription processing, secure point-of-sale transactions, structured auditing, and real-time alerts**.

---

## 🗺️ Architectural Topology

The application utilizes a distributed, multi-tiered cloud architecture designed for high availability, security, and autoscaling.

```
                  ┌──────────────────────────────────────────────┐
                  │              Client Interfaces               │
                  │  ┌──────────────────┐  ┌──────────────────┐  │
                  │  │ React Web Client │  │ Flutter App      │  │
                  │  │ (pharmasync-hub) │  │ (Mobile/Desktop) │  │
                  │  └────────┬─────────┘  └────────┬─────────┘  │
                  └───────────┼─────────────────────┼────────────┘
                              │                     │
                              ▼                     ▼
                  ┌──────────────────────────────────────────────┐
                  │               Public Routing                 │
                  │      ┌──────────────────────────────┐        │
                  │      │  Application Load Balancers  │        │
                  │      │  (main_frontend / backend)   │        │
                  │      └──────────────┬───────────────┘        │
                  └─────────────────────┼────────────────────────┘
                                        │
========================================┼========================================
AWS VPC (10.1.0.0/16)                   │
                                        ▼
                  ┌──────────────────────────────────────────────┐
                  │           Private Subnets (ASG)              │
                  │  ┌──────────────────┐  ┌──────────────────┐  │
                  │  │   Frontend ASG   │  │   Backend ASG    │  │
                  │  │  (Vite Web App)  │  │ (FastAPI Server) │  │
                  │  └──────────────────┘  └────────┬─────────┘  │
                  └─────────────────────────────────┼────────────┘
                                                    │
                                                    ▼
                  ┌──────────────────────────────────────────────┐
                  │                 Database Tier                │
                  │          ┌──────────────────────┐            │
                  │          │  AWS RDS PostgreSQL  │            │
                  │          └──────────────────────┘            │
                  └──────────────────────────────────────────────┘
```

---

## 📂 Repository Structure

The project is structured into three primary sub-systems, alongside modular infrastructure configurations:

1. **Backend API (`pharmacloud-api`)**: FastAPI service driving all business logic, tenant isolation, and transactional workflows.
2. **Web Portal Client (`pharmasync-hub`)**: Vite + React + TypeScript single-page dashboard optimized for operational administrators and analysts.
3. **Mobile & Desktop App (`flutter_pharmacy`)**: Cross-platform Dart application optimized for on-the-ground pharmacists, dispensing agents, and managers.
4. **Infrastructure Setup (`Terraform Labs/build`)**: Complete Infrastructure as Code (IaC) configuration for deploying this suite onto AWS.

---

### 1. ⚙️ Backend Core API: [pharmacloud-api](file:///d:/LAB/Pharmacy/pharmacloud-api)

The backend services are engineered with **FastAPI** to support asynchronous database interaction and sub-millisecond response latency.

* **Key File References**:
  * **API Entrypoint**: [main.py](file:///d:/LAB/Pharmacy/pharmacloud-api/app/main.py)
  * **Database Setup**: [database.py](file:///d:/LAB/Pharmacy/pharmacloud-api/app/shared/database.py)
  * **System Configuration**: [config.py](file:///d:/LAB/Pharmacy/pharmacloud-api/app/config.py)
  * **Models Registry**: [models.py](file:///d:/LAB/Pharmacy/pharmacloud-api/app/models.py)
  * **Pre-population & Seeding**: [seed.py](file:///d:/LAB/Pharmacy/pharmacloud-api/seed.py)

#### Core Logic Submodules
* **[tenants](file:///d:/LAB/Pharmacy/pharmacloud-api/app/tenants)**: Manages tenant context and branch assignments. Uses PostgreSQL row-level isolation patterns.
* **[auth](file:///d:/LAB/Pharmacy/pharmacloud-api/app/auth)**: Secure token emission using OAuth2 with password flow, encrypted with standard JWT.
* **[inventory](file:///d:/LAB/Pharmacy/pharmacloud-api/app/inventory)**: Tracks medicine cataloging, batch numbers, categories, expirations, and stock levels.
* **[sales](file:///d:/LAB/Pharmacy/pharmacloud-api/app/sales)**: Point of sale transaction logging, invoice creation, and payment verification.
* **[procurement](file:///d:/LAB/Pharmacy/pharmacloud-api/app/procurement)**: Manages supplier interactions, purchase ordering, and intake reconciliation.
* **[prescriptions](file:///d:/LAB/Pharmacy/pharmacloud-api/app/prescriptions)**: Processes digital and physical medical prescriptions, linking them to customer profiles.
* **[audit](file:///d:/LAB/Pharmacy/pharmacloud-api/app/audit)**: Logs immutable activities and logs user operations for compliance.

---

### 2. 💻 React Web Hub: [pharmasync-hub](file:///d:/LAB/Pharmacy/pharmasync-hub)

The React web client provides management interfaces for reporting, metrics, billing, tenant creation, and configuration management.

* **Key File References**:
  * **Vite Configuration**: [vite.config.ts](file:///d:/LAB/Pharmacy/pharmasync-hub/vite.config.ts)
  * **Base Styles**: [styles.css](file:///d:/LAB/Pharmacy/pharmasync-hub/src/styles.css)
  * **App Root Router**: [__root.tsx](file:///d:/LAB/Pharmacy/pharmasync-hub/src/routes/__root.tsx)
  * **Router Configuration**: [router.tsx](file:///d:/LAB/Pharmacy/pharmasync-hub/src/router.tsx)
  * **Unified App Layout & State**: [app.tsx](file:///d:/LAB/Pharmacy/pharmasync-hub/src/routes/app.tsx)
  * **Main Dashboard**: [app.index.tsx](file:///d:/LAB/Pharmacy/pharmasync-hub/src/routes/app.index.tsx)

---

### 3. 📱 Cross-Platform Flutter App: [flutter_pharmacy](file:///d:/LAB/Pharmacy/flutter_pharmacy)

The client application is built in Dart & Flutter, supporting Android, iOS, Windows, macOS, and Linux targets.

* **Key File References**:
  * **Application Main entrypoint**: [main.dart](file:///d:/LAB/Pharmacy/flutter_pharmacy/lib/main.dart)
  * **Dynamic Workspace Provider**: [workspace_provider.dart](file:///d:/LAB/Pharmacy/flutter_pharmacy/lib/providers/workspace_provider.dart)
  * **Network Client API Service**: [api_service.dart](file:///d:/LAB/Pharmacy/flutter_pharmacy/lib/services/api_service.dart)
  * **UI Login Page**: [login_screen.dart](file:///d:/LAB/Pharmacy/flutter_pharmacy/lib/screens/login_screen.dart)
  * **UI Workspace Settings**: [settings_screen.dart](file:///d:/LAB/Pharmacy/flutter_pharmacy/lib/screens/settings_screen.dart)

#### Key Operational Features
* **Adaptive API Target Routing**: Users can switch target backends directly from the Login page or from the Settings panel.
* **Intelligent Cookie & Cache Clearing**: When switching backend host targets, the provider invalidates existing JWT sessions, resets client caches, and logs out the user to prevent cross-tenant data leaks.
* **Robust Network Service**: Configured with a 10–15s connection request limit to accommodate variable cellular and cloud load latency, featuring automated header validation.

---

## ☁️ Infrastructure-As-Code (IaC) Architecture

The infrastructure configuration reside inside the Terraform directory: [Terraform Labs/build](file:///D:/LAB/Terraform Labs/build).

| File Name | Purpose / Resource Definition |
| :--- | :--- |
| **[vpc.tf](file:///D:/LAB/Terraform Labs/build/vpc.tf)** | Establishes the AWS VPC with CIDR `10.1.0.0/16`. |
| **[subnet.tf](file:///D:/LAB/Terraform Labs/build/subnet.tf)** | Provisions 3 Public subnets (`10.1.1.0/24`, `10.1.2.0/24`, `10.1.3.0/24`) and 3 Private subnets (`10.1.11.0/24`, `10.1.12.0/24`, `10.1.13.0/24`) across Availability Zones `eu-central-1a/b/c`. |
| **[nat.tf](file:///D:/LAB/Terraform Labs/build/nat.tf)** | Provisions Elastic IP and AWS NAT Gateway inside public subnets, letting private instances run outbound updates. |
| **[route.tf](file:///D:/LAB/Terraform Labs/build/route.tf)** | Configures routing tables connecting Public subnets to Internet Gateway and Private subnets to NAT Gateway. |
| **[sg.tf](file:///D:/LAB/Terraform Labs/build/sg.tf)** | Restricts ports dynamically. Backend instances receive traffic **only** from the backend load balancer on port `8000`. Frontend instances receive traffic **only** from the frontend load balancer. |
| **[alb.tf](file:///D:/LAB/Terraform Labs/build/alb.tf)** | Launches the Frontend application load balancer (port 80/443) and Backend application load balancer (port 80/443). |
| **[tg.tf](file:///D:/LAB/Terraform Labs/build/tg.tf)** | Sets up target groups with load-balancer sticky cookies (`lb_cookie`) and HTTP health checks on `/` for web and `/health` for API. |
| **[asg.tf](file:///D:/LAB/Terraform Labs/build/asg.tf)** | Configures ASG scales between 2 and 3 instances using private subnet placement. Includes sequential delay timers to wait for seeding to complete. |
| **[ec2.tf](file:///D:/LAB/Terraform Labs/build/ec2.tf)** | Provisions launch templates detailing AMI config, startup scripts, and instance metadata. |
| **[rds.tf](file:///D:/LAB/Terraform Labs/build/rds.tf)** | Provisions an AWS RDS instance executing PostgreSQL v17, assigned within a custom database subnet group. |
| **[seed_ec2.tf](file:///D:/LAB/Terraform Labs/build/seed_ec2.tf)** | Configures an ephemeral database-seeding instance (`db_seed`) running [seed_startup.sh](file:///D:/LAB/Terraform Labs/build/seed_startup.sh) to apply schema migrations and populate data, terminating on script success. |

---

## 🚀 Deployment & Local Development

### 1. Database & Backend API Setup
Copy `.env.example` to `.env` inside [pharmacloud-api](file:///d:/LAB/Pharmacy/pharmacloud-api) and adjust variables:
```bash
DATABASE_URL=postgresql://<user>:<password>@localhost:5432/pharmacy
JWT_SECRET=your_jwt_secret_key
JWT_ALGORITHM=HS256
```

Initialize your virtual environment, install dependencies, and run:
```bash
cd pharmacloud-api
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

### 2. Frontend Web Portal Setup
Configure local environments inside [pharmasync-hub](file:///d:/LAB/Pharmacy/pharmasync-hub) in `.env`:
```bash
VITE_API_BASE_URL=http://localhost:8000
```

Install packages and boot the local dev server:
```bash
cd pharmasync-hub
npm install
npm run dev
```

### 3. Mobile/Desktop Frontend Setup
Adjust server endpoint values inside the local configuration file:
* **Settings**: [config.yaml](file:///d:/LAB/Pharmacy/flutter_pharmacy/config.yaml)

Install Flutter dependencies and run the application:
```bash
cd flutter_pharmacy
flutter pub get
flutter run
```

### 4. Deploying to AWS via Terraform
Navigate to the Terraform directory [Terraform Labs/build](file:///D:/LAB/Terraform Labs/build):
```bash
cd "D:\LAB\Terraform Labs\build"
terraform init
terraform plan
terraform apply --auto-approve
```
Once deployed, the `outputs.tf` script will return the active **ALB DNS Endpoints** for the frontend and backend. You can use these endpoints to connect the React portal and Flutter clients to your newly spawned cloud system!
