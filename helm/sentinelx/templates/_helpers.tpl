{{/*
Expand the name of the chart.
*/}}
{{- define "sentinelx.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "sentinelx.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "sentinelx.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "sentinelx.namespace" -}}
{{- .Values.namespace.name }}
{{- end }}

{{- define "sentinelx.labels" -}}
helm.sh/chart: {{ include "sentinelx.chart" . }}
{{ include "sentinelx.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "sentinelx.selectorLabels" -}}
app.kubernetes.io/name: {{ include "sentinelx.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "sentinelx.componentLabels" -}}
{{ include "sentinelx.selectorLabels" . }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{- define "sentinelx.image" -}}
{{- $registry := .Values.global.imageRegistry -}}
{{- $repo := .repository -}}
{{- $tag := .tag | default "latest" -}}
{{- if $registry -}}
{{- printf "%s/%s:%s" $registry $repo $tag -}}
{{- else -}}
{{- printf "%s:%s" $repo $tag -}}
{{- end }}
{{- end }}

{{- define "sentinelx.secretName" -}}
{{- printf "%s-secrets" (include "sentinelx.fullname" .) }}
{{- end }}

{{- define "sentinelx.configMapName" -}}
{{- printf "%s-config" (include "sentinelx.fullname" .) }}
{{- end }}

{{- define "sentinelx.dbPassword" -}}
{{- .Values.secrets.dbPassword | default .Values.postgresql.auth.password -}}
{{- end }}

{{- define "sentinelx.dbUser" -}}
{{- .Values.secrets.dbUser | default .Values.postgresql.auth.username -}}
{{- end }}

{{- define "sentinelx.dbHost" -}}
{{- if .Values.backend.externalDbHost -}}
{{- .Values.backend.externalDbHost -}}
{{- else if .Values.postgresql.enabled -}}
{{- .Values.postgresql.serviceName -}}
{{- else -}}
{{- required "backend.externalDbHost is required when postgresql.enabled=false" .Values.backend.externalDbHost -}}
{{- end }}
{{- end }}

{{- define "sentinelx.redisHost" -}}
{{- if .Values.backend.externalRedisHost -}}
{{- .Values.backend.externalRedisHost -}}
{{- else if .Values.redis.enabled -}}
{{- .Values.redis.serviceName -}}
{{- else -}}
{{- required "backend.externalRedisHost is required when redis.enabled=false" .Values.backend.externalRedisHost -}}
{{- end }}
{{- end }}

{{- define "sentinelx.postgresql.fullname" -}}
{{- printf "%s-postgresql" (include "sentinelx.fullname" .) }}
{{- end }}

{{- define "sentinelx.postgresql.headlessServiceName" -}}
{{- printf "%s-headless" .Values.postgresql.serviceName }}
{{- end }}

{{- define "sentinelx.redis.fullname" -}}
{{- printf "%s-redis" (include "sentinelx.fullname" .) }}
{{- end }}

{{- define "sentinelx.redis.headlessServiceName" -}}
{{- printf "%s-headless" .Values.redis.serviceName }}
{{- end }}

{{- define "sentinelx.backend.fullname" -}}
{{- printf "%s-backend" (include "sentinelx.fullname" .) }}
{{- end }}

{{- define "sentinelx.frontend.fullname" -}}
{{- printf "%s-frontend" (include "sentinelx.fullname" .) }}
{{- end }}
