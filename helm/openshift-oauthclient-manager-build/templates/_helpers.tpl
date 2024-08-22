{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "openshift-oauthclient-manager-build.name" -}}
{{-   default .Chart.Name .Values.nameOverride | replace "-openshift-build" "" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "openshift-oauthclient-manager-build.chart" -}}
{{-   printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "openshift-oauthclient-manager-build.labels" -}}
helm.sh/chart: {{ include "openshift-oauthclient-manager-build.chart" . }}
app.kubernetes.io/name: {{ include "openshift-oauthclient-manager-build.name" . }}
{{-   if (ne (lower .Release.Name) "release-name") }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{-   end -}}
{{-   if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{-   end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
