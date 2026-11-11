import { useState } from 'react';
import { Text } from 'react-native';

import { requestOtp, verifyOtp } from '@/api/endpoints';
import { useAuth } from '@/auth/AuthContext';
import { errorMessage, t } from '@/i18n';
import { normalizePhone } from '@/lib/phone';
import { Button, Field, Notice, Screen } from '@/ui/components';
import { useTheme } from '@/ui/theme';

/** Phone, then the SMS code. The account is created by the server on first login. */
export default function LoginScreen() {
  const { signIn } = useAuth();
  const { font, mode, toggleTheme } = useTheme();
  const [phoneInput, setPhoneInput] = useState('+7');
  const [phone, setPhone] = useState<string | null>(null); // set once a code has been sent
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      await action();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  function sendCode() {
    const normalized = normalizePhone(phoneInput);
    if (!normalized) {
      setError(t.login.phoneInvalid);
      return;
    }
    void run(async () => {
      await requestOtp(normalized);
      setPhone(normalized);
      setCode('');
    });
  }

  function resend() {
    if (!phone) return;
    void run(async () => {
      await requestOtp(phone);
      setInfo(t.login.resent);
    });
  }

  function submitCode() {
    if (!phone) return;
    if (!/^\d{4,8}$/.test(code)) {
      setError(t.login.codeInvalid);
      return;
    }
    void run(async () => signIn(await verifyOtp(phone, code)));
  }

  if (phone === null) {
    return (
      <Screen>
        <Text style={font.body}>{t.login.subtitle}</Text>
        <Field
          label={t.login.phoneLabel}
          value={phoneInput}
          onChangeText={setPhoneInput}
          placeholder={t.login.phoneHint}
          keyboardType="phone-pad"
          autoComplete="tel"
          textContentType="telephoneNumber"
          returnKeyType="done"
          onSubmitEditing={sendCode}
          autoFocus
        />
        {error ? <Notice>{error}</Notice> : null}
        <Button title={t.login.sendCode} onPress={sendCode} loading={busy} />
        <Button
          title={mode === 'light' ? t.theme.switchToDark : t.theme.switchToLight}
          variant="link"
          onPress={toggleTheme}
        />
      </Screen>
    );
  }

  return (
    <Screen>
      <Text style={font.heading}>{t.login.codeTitle}</Text>
      <Text style={font.body}>{t.login.codeSubtitle(phone)}</Text>
      <Field
        label={t.login.codeLabel}
        value={code}
        onChangeText={(value) => setCode(value.replace(/\D/g, ''))}
        keyboardType="number-pad"
        autoComplete="one-time-code"
        textContentType="oneTimeCode"
        maxLength={8}
        returnKeyType="done"
        onSubmitEditing={submitCode}
        autoFocus
      />
      {error ? <Notice>{error}</Notice> : null}
      {info ? <Notice tone="info">{info}</Notice> : null}
      <Button title={t.login.signIn} onPress={submitCode} loading={busy} />
      <Button title={t.login.resend} variant="link" onPress={resend} disabled={busy} />
      <Button
        title={t.login.changePhone}
        variant="link"
        disabled={busy}
        onPress={() => {
          setPhone(null);
          setError(null);
          setInfo(null);
        }}
      />
    </Screen>
  );
}
