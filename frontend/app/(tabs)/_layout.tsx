import { Tabs } from 'expo-router';
import { Feather } from '@expo/vector-icons';
import { colors } from '../../src/theme';
import { Platform } from 'react-native';

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textTertiary,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          borderTopWidth: 1,
          height: Platform.OS === 'ios' ? 88 : 64,
          paddingTop: 8,
          paddingBottom: Platform.OS === 'ios' ? 28 : 8,
        },
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{ title: 'Today', tabBarIcon: ({ color, size }) => <Feather name="sun" color={color} size={size} /> }}
      />
      <Tabs.Screen
        name="goals"
        options={{ title: 'Goals', tabBarIcon: ({ color, size }) => <Feather name="target" color={color} size={size} /> }}
      />
      <Tabs.Screen
        name="review"
        options={{ title: 'Review', tabBarIcon: ({ color, size }) => <Feather name="bar-chart-2" color={color} size={size} /> }}
      />
      <Tabs.Screen
        name="profile"
        options={{ title: 'Profile', tabBarIcon: ({ color, size }) => <Feather name="user" color={color} size={size} /> }}
      />
    </Tabs>
  );
}
