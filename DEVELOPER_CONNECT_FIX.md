# Fix for Google Cloud Developer Connect Invalid Image Name Error

## Problem

Google Cloud Developer Connect is failing with the error:

```
invalid build: invalid image name "europe-west1-docker.pkg.dev/activitytracker-480123/cloud-run-source-deploy/DailyAccomplishments/dailyaccomplishments-git:c877dc8444717851b03ade7a943ac2d4065ea7e2": could not parse reference
```

## Root Cause

The Developer Connect connection `cloudrun-dailyaccomplishments-git-europe-west1-johnlicataptbgbq` is auto-generating an invalid Docker image name that:

1. Includes the GitHub repository name "DailyAccomplishments" with capital letters (invalid for Docker)
2. Creates a nested path structure that Artifact Registry doesn't support

## Solution

The issue must be fixed in the Google Cloud Console by reconfiguring the Developer Connect connection:

### Option 1: Reconfigure the Existing Connection (Recommended)

1. Go to [Google Cloud Console > Developer Connect](https://console.cloud.google.com/developer-connect)
2. Select the project: `activitytracker-480123`
3. Find the connection: `cloudrun-dailyaccomplishments-git-europe-west1-johnlicataptbgbq`
4. Click **Edit** or **Configure**
5. In the **Build Configuration** section:
   - Select **Use custom build configuration file**
   - Specify the file path: `cloudbuild.yaml` (in the root directory)
6. Save the configuration

### Option 2: Delete and Recreate the Connection

1. Delete the existing connection `cloudrun-dailyaccomplishments-git-europe-west1-johnlicataptbgbq`
2. Create a new Cloud Run connection with these settings:
   - **Repository**: johnlicataptbiz/DailyAccomplishments
   - **Branch**: main (or your default branch)
   - **Build Configuration**: Custom - use `cloudbuild.yaml`
   - **Region**: europe-west1
   - **Service Name**: dailyaccomplishments (lowercase, no extra path segments)

### Option 3: Use Cloud Build Triggers Instead

As an alternative, you can bypass Developer Connect and use Cloud Build Triggers directly:

1. Go to [Cloud Build > Triggers](https://console.cloud.google.com/cloud-build/triggers)
2. Create a new trigger:
   - **Event**: Push to branch
   - **Source**: johnlicataptbiz/DailyAccomplishments
   - **Branch**: ^main$
   - **Configuration**: Cloud Build configuration file
   - **Location**: Repository - `cloudbuild.yaml`
3. This will use the existing `cloudbuild.yaml` which has the correct image naming

## Verification

After applying the fix, the next commit should trigger a successful build with the correct image name:

```
europe-west1-docker.pkg.dev/activitytracker-480123/cloud-run-source-deploy/dailyaccomplishments:COMMIT_SHA
```

Note: No capital letters, no extra path segments.

## Technical Details

The repository already contains a properly configured `cloudbuild.yaml` that:
- Uses lowercase image names
- Follows Docker naming conventions
- Deploys to Cloud Run successfully

The issue is purely a configuration problem with how Developer Connect is invoking the build.
