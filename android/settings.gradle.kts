pluginManagement {
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}
plugins {
    id("org.gradle.toolchains.foojay-resolver-convention") version "0.10.0"
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "SynapseAI"
include(":app")
// include(":bridge") // Add bridge when needed

// Redirect build outputs outside OneDrive to avoid Windows file locking during sync
val buildDirBase = file("C:/Users/midun/.synapse_build")
gradle.beforeProject {
    val relativePath = project.projectDir.relativeTo(rootDir).path
    project.layout.buildDirectory.set(if (relativePath.isEmpty()) File(buildDirBase, "root") else File(buildDirBase, relativePath))
}

