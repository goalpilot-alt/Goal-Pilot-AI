import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';
import { api } from './api';

// Foreground display behavior
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
    shouldShowBanner: true,
    shouldShowList: true,
  }) as any,
});

export type Task = { id: string; title: string; due_date: string; completed: boolean; priority: string };

export async function ensureAndroidChannel() {
  if (Platform.OS !== 'android') return;
  try {
    await Notifications.setNotificationChannelAsync('reminders', {
      name: 'Reminders',
      importance: Notifications.AndroidImportance.DEFAULT,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#FF5E00',
    });
  } catch {}
}

export async function requestPermissions(): Promise<boolean> {
  if (Platform.OS === 'web') return false;
  try {
    const { status: existing } = await Notifications.getPermissionsAsync();
    let final = existing;
    if (existing !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      final = status;
    }
    return final === 'granted';
  } catch {
    return false;
  }
}

export async function getAndRegisterPushToken(): Promise<string | null> {
  if (Platform.OS === 'web' || !Device.isDevice) return null;
  try {
    const granted = await requestPermissions();
    if (!granted) return null;
    const tokenData = await Notifications.getExpoPushTokenAsync();
    const token = tokenData?.data;
    if (token) {
      try {
        await api.post('/notifications/token', { token, platform: Platform.OS });
      } catch {}
      return token;
    }
  } catch {}
  return null;
}

function reminderTimeForDate(dateStr: string): Date {
  // 9:00 AM local on the task's due_date
  const [y, m, d] = dateStr.split('-').map(n => parseInt(n, 10));
  const dt = new Date();
  dt.setFullYear(y, (m || 1) - 1, d || 1);
  dt.setHours(9, 0, 0, 0);
  return dt;
}

export async function scheduleTaskReminders(tasks: Task[]) {
  if (Platform.OS === 'web') return;
  const granted = await requestPermissions();
  if (!granted) return;
  await ensureAndroidChannel();

  // Wipe & re-schedule for simplicity
  try { await Notifications.cancelAllScheduledNotificationsAsync(); } catch {}

  const now = Date.now();
  const upcoming = tasks
    .filter(t => !t.completed)
    .map(t => ({ ...t, when: reminderTimeForDate(t.due_date) }))
    .filter(t => t.when.getTime() > now)
    .slice(0, 30);

  for (const t of upcoming) {
    try {
      await Notifications.scheduleNotificationAsync({
        content: {
          title: 'GoalPilot reminder',
          body: t.title,
          data: { task_id: t.id, goal_id: (t as any).goal_id },
        },
        trigger: {
          type: Notifications.SchedulableTriggerInputTypes.DATE,
          date: t.when,
        } as any,
      });
    } catch {}
  }
}

export async function cancelAllReminders() {
  if (Platform.OS === 'web') return;
  try { await Notifications.cancelAllScheduledNotificationsAsync(); } catch {}
}
