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
        // 🔹 Aggiunta: Dokka repository
        maven("https://maven.pkg.jetbrains.space/public/p/dokka/maven")
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        // 🔹 Aggiunta: Dokka repository
        maven("https://maven.pkg.jetbrains.space/public/p/dokka/maven")
    }
}

rootProject.name = "Example_app"
include(":app")

