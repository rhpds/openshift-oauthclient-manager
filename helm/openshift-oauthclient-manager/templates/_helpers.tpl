{{/* vim: set filetype=mustache: */}}
{{- define "openshift-oauthclient-manager.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "openshift-oauthclient-manager.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "openshift-oauthclient-manager.labels" -}}
helm.sh/chart: {{ include "openshift-oauthclient-manager.chart" . }}
{{ include "openshift-oauthclient-manager.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "openshift-oauthclient-manager.selectorLabels" -}}
app.kubernetes.io/name: {{ include "openshift-oauthclient-manager.name" . }}
{{-   if (ne (lower .Release.Name) "release-name") }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{-   end -}}
{{- end -}}

{{/*
Create the name of the service account to use
*/}}
{{- define "openshift-oauthclient-manager.serviceAccountName" -}}
{{- if .Values.odo -}}
default
{{- else if .Values.serviceAccount.create -}}
{{ default (include "openshift-oauthclient-manager.name" .) .Values.serviceAccount.name }}
{{- else -}}
{{ default "default" .Values.serviceAccount.name }}
{{- end -}}
{{- end -}}

{{/*
Create the name of the namespace to use
*/}}
{{- define "openshift-oauthclient-manager.namespaceName" -}}
{{- if .Values.namespace.create -}}
    {{ default (include "openshift-oauthclient-manager.name" .) .Values.namespace.name }}
{{- else -}}
    {{ default "default" .Values.namespace.name }}
{{- end -}}
{{- end -}}

{{/*
Define the image to deploy
*/}}
{{- define "openshift-oauthclient-manager.image" -}}
  {{- if .Values.image.override -}}
    {{- .Values.image.override -}}
  {{- else if .Values.image.tag -}}
    {{- printf "%s:%s" .Values.image.repository .Values.image.tag -}}
  {{- else -}}
    {{- printf "%s:v%s" .Values.image.repository .Chart.AppVersion -}}
  {{- end -}}
{{- end -}}
