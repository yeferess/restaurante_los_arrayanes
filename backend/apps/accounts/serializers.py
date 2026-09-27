from rest_framework import serializers


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class MeseroLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    pin = serializers.CharField()


class CreateMeseroSerializer(serializers.Serializer):
    username = serializers.CharField()
    pin = serializers.CharField()


class ResetMeseroPinSerializer(serializers.Serializer):
    nuevo_pin = serializers.CharField()


class CreateAdminSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class ChangeOwnPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField()
    password_nueva = serializers.CharField()
    password_nueva_confirmacion = serializers.CharField()
