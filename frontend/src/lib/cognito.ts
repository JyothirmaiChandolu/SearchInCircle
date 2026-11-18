const REGION = process.env.EXPO_PUBLIC_COGNITO_REGION;
const CLIENT_ID = process.env.EXPO_PUBLIC_COGNITO_CLIENT_ID;
const ENDPOINT = `https://cognito-idp.${REGION}.amazonaws.com/`;

export class CognitoError extends Error {
  constructor(
    message: string,
    public code: string,
  ) {
    super(message);
  }
}

export type TokensResult = {
  accessToken: string;
  idToken: string;
  refreshToken: string;
  expiresIn: number;
};

async function cognitoRequest<T>(target: string, body: Record<string, unknown>): Promise<T> {
  const response = await fetch(ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-amz-json-1.1',
      'X-Amz-Target': `AWSCognitoIdentityProviderService.${target}`,
    },
    body: JSON.stringify(body),
  });

  const data = await response.json();

  if (!response.ok) {
    const code = typeof data?.__type === 'string' ? data.__type.split('#').pop() : 'UnknownError';
    const message = typeof data?.message === 'string' ? data.message : 'Request failed';
    throw new CognitoError(message, code);
  }

  return data as T;
}

/**
 * Starts sign-in for a phone number. New numbers are signed up on the spot
 * (Cognito sends the confirmation code, which doubles as the first login
 * code); existing numbers go straight to a login OTP challenge.
 */
export async function startPhoneAuth(
  e164Phone: string,
): Promise<{ mode: 'signup' | 'login'; session: string }> {
  try {
    const result = await cognitoRequest<{ Session: string }>('SignUp', {
      ClientId: CLIENT_ID,
      Username: e164Phone,
      UserAttributes: [{ Name: 'phone_number', Value: e164Phone }],
    });
    return { mode: 'signup', session: result.Session };
  } catch (err) {
    if (err instanceof CognitoError && err.code === 'UsernameExistsException') {
      const result = await cognitoRequest<{ Session: string; ChallengeName: string }>('InitiateAuth', {
        AuthFlow: 'USER_AUTH',
        ClientId: CLIENT_ID,
        AuthParameters: { USERNAME: e164Phone, PREFERRED_CHALLENGE: 'SMS_OTP' },
      });
      return { mode: 'login', session: result.Session };
    }
    throw err;
  }
}

/** Confirms a new sign-up with the code Cognito sent, and signs the user straight in. */
export async function confirmSignUpAndLogin(e164Phone: string, code: string, session: string): Promise<TokensResult> {
  const confirmed = await cognitoRequest<{ Session: string }>('ConfirmSignUp', {
    ClientId: CLIENT_ID,
    Username: e164Phone,
    ConfirmationCode: code,
    Session: session,
  });

  const result = await cognitoRequest<{ AuthenticationResult: CognitoAuthResult }>('InitiateAuth', {
    AuthFlow: 'USER_AUTH',
    ClientId: CLIENT_ID,
    AuthParameters: { USERNAME: e164Phone },
    Session: confirmed.Session,
  });

  return fromAuthResult(result.AuthenticationResult);
}

/** Verifies the OTP code for a returning user's login challenge. */
export async function verifyLoginOtp(e164Phone: string, code: string, session: string): Promise<TokensResult> {
  const result = await cognitoRequest<{ AuthenticationResult: CognitoAuthResult }>('RespondToAuthChallenge', {
    ClientId: CLIENT_ID,
    ChallengeName: 'SMS_OTP',
    Session: session,
    ChallengeResponses: { USERNAME: e164Phone, SMS_OTP_CODE: code },
  });

  return fromAuthResult(result.AuthenticationResult);
}

/** Exchanges a stored refresh token for a fresh access/id token pair. */
export async function refreshSession(refreshToken: string): Promise<Omit<TokensResult, 'refreshToken'>> {
  const result = await cognitoRequest<{ AuthenticationResult: CognitoAuthResult }>('InitiateAuth', {
    AuthFlow: 'REFRESH_TOKEN_AUTH',
    ClientId: CLIENT_ID,
    AuthParameters: { REFRESH_TOKEN: refreshToken },
  });

  const auth = result.AuthenticationResult;
  return { accessToken: auth.AccessToken, idToken: auth.IdToken, expiresIn: auth.ExpiresIn };
}

type CognitoAuthResult = { AccessToken: string; IdToken: string; RefreshToken: string; ExpiresIn: number };

function fromAuthResult(auth: CognitoAuthResult): TokensResult {
  return {
    accessToken: auth.AccessToken,
    idToken: auth.IdToken,
    refreshToken: auth.RefreshToken,
    expiresIn: auth.ExpiresIn,
  };
}
