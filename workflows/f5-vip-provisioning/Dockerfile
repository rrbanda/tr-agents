FROM docker.io/apache/incubator-kie-sonataflow-builder:10.1.0 AS builder

COPY src/main/resources/ /home/kogito/serverless-workflow-project/src/main/resources/

RUN /usr/share/maven/bin/mvnw -B \
    -Dmaven.compiler.release=17 \
    -Duser.home=/home/kogito \
    -s /home/kogito/.m2/settings.xml \
    -DskipTests \
    -Dquarkus.analytics.disabled=true \
    -Dquarkus.http.host=0.0.0.0 \
    package -f /home/kogito/serverless-workflow-project/pom.xml

FROM registry.access.redhat.com/ubi9/openjdk-17-runtime:1.23

COPY --from=builder /home/kogito/serverless-workflow-project/target/quarkus-app/ /deployments/

ENV JAVA_OPTS_APPEND="-Dquarkus.http.host=0.0.0.0 -Dquarkus.http.port=8080"
EXPOSE 8080
