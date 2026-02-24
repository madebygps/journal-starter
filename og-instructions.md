1. Write a Dockerfile at the root of your repository that packages your Journal API into a container image. Build and test it locally before pushing to a registry.

2. Create Terraform configuration files in an infra/ directory to define and provision your cloud infrastructure.

3. Apply the GitHub Actions workflow you built in the CI/CD Pipelines topic to your Journal API repository. Ensure it automatically builds, tests, and deploys your application on every push to main.

4. Write Kubernetes manifests in a k8s/ directory to deploy and expose your containerized application.

5. Set up monitoring to track your application's health and performance. This step is not auto-verified but is essential for production readiness.

6. Your repository must include these directories and files for auto-verification. Steps 1–4 are verified automatically when you submit your repo URL.

your-journal-starter/
  ├── Dockerfile              # Step 1: Container definition
  ├── .github/
  │   └── workflows/          # Step 3: CI/CD pipeline configs
  │       └── *.yml
  ├── infra/                   # Step 2: Terraform IaC configs
  │   ├── main.tf
  │   └── variables.tf
  ├── k8s/                     # Step 4: Kubernetes manifests
  │   ├── deployment.yaml
  │   └── service.yaml
  ├── api/                     # Your FastAPI app code
  └── README.md                # Step 6: Documentation
