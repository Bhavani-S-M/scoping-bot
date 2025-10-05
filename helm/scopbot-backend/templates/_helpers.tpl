{{- define "scopbot-backend.name" -}}
backend
{{- end }}

{{- define "scopbot-backend.fullname" -}}
{{ .Chart.Name }}
{{- end }}
