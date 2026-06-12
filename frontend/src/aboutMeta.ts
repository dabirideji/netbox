import { isNetboxDesktop } from './platform';

export const aboutAppName = __NETBOX_APP_NAME__;
export const aboutVersion = __NETBOX_APP_VERSION__;
export const aboutOpenSource = __NETBOX_OPEN_SOURCE__;
export const aboutAppId = __NETBOX_APP_ID__;
export const aboutCopyright = __NETBOX_BUILD_COPYRIGHT__;
export const aboutBuilder = `${__NETBOX_BUILDER_NAME__} ${__NETBOX_BUILDER_VERSION__}`;
export const aboutAuthor = __NETBOX_BUILD_AUTHOR__;

export function aboutRuntimeLabel(): string {
  return isNetboxDesktop() ? 'Desktop app' : 'Browser';
}
