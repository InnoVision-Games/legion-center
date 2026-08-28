import { FileSelectionType, openFilePicker } from '@decky/api';
import {
  ButtonItem,
  ConfirmModal,
  Field,
  PanelSectionRow,
  showModal
} from '@decky/ui';
import { useState } from 'react';
import { useDispatch } from 'react-redux';
import { exportFanProfiles, importFanProfiles } from '../../backend/utils';
import { fanSlice } from '../../redux-modules/fanSlice';

type TransferStatus = {
  kind: 'success' | 'error';
  message: string;
};

const wasCancelled = (error: unknown) =>
  String(error).toLocaleLowerCase().includes('cancel');

const filename = (path?: string) => {
  const parts = path?.split('/').filter(Boolean) || [];
  return parts[parts.length - 1];
};

const FanProfileTools = () => {
  const dispatch = useDispatch();
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<TransferStatus>();

  const exportProfiles = async () => {
    if (busy) return;
    setBusy(true);
    setStatus(undefined);
    try {
      const selection = await openFilePicker(
        FileSelectionType.FOLDER,
        '/home/deck',
        false,
        true
      );
      const result = await exportFanProfiles(
        selection.realpath || selection.path
      );
      setStatus(
        result.success
          ? {
              kind: 'success',
              message: `Saved ${filename(result.path) || 'fan profile backup'}`
            }
          : {
              kind: 'error',
              message: result.error || 'Could not export fan profiles'
            }
      );
    } catch (error) {
      if (!wasCancelled(error)) {
        setStatus({
          kind: 'error',
          message:
            error instanceof Error
              ? error.message
              : 'Could not export fan profiles'
        });
      }
    } finally {
      setBusy(false);
    }
  };

  const performImport = async (path: string) => {
    setBusy(true);
    setStatus(undefined);
    try {
      const result = await importFanProfiles(path);
      if (result.success && result.profiles) {
        dispatch(fanSlice.actions.updateFanProfiles(result.profiles));
        const backup = filename(result.backupPath);
        setStatus({
          kind: 'success',
          message: `Imported ${result.count ?? 0} profile${
            result.count === 1 ? '' : 's'
          }${backup ? `; previous profiles saved as ${backup}` : ''}`
        });
      } else {
        setStatus({
          kind: 'error',
          message: result.error || 'Could not import fan profiles'
        });
      }
    } catch (error) {
      setStatus({
        kind: 'error',
        message:
          error instanceof Error
            ? error.message
            : 'Could not import fan profiles'
      });
    } finally {
      setBusy(false);
    }
  };

  const chooseImport = async () => {
    if (busy) return;
    setStatus(undefined);
    try {
      const selection = await openFilePicker(
        FileSelectionType.FILE,
        '/home/deck',
        true,
        false,
        undefined,
        ['json'],
        false,
        false,
        1
      );
      const path = selection.realpath || selection.path;
      showModal(
        <ConfirmModal
          strTitle="Import fan profiles?"
          strDescription={
            'Profiles with matching game IDs will be replaced and new profiles ' +
            'will be added. Legion Center will save a recovery backup before ' +
            'making changes.'
          }
          strOKButtonText="Import"
          onOK={() => {
            void performImport(path);
          }}
        />
      );
    } catch (error) {
      if (!wasCancelled(error)) {
        setStatus({
          kind: 'error',
          message:
            error instanceof Error
              ? error.message
              : 'Could not select a fan profile file'
        });
      }
    }
  };

  return (
    <>
      <PanelSectionRow>
        <ButtonItem
          label="Export Fan Profiles"
          description="Save every global and per-game curve as a portable JSON backup"
          disabled={busy}
          onClick={() => void exportProfiles()}
        >
          Export
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem
          label="Import Fan Profiles"
          description="Merge a Legion Center JSON backup and preserve a recovery copy"
          disabled={busy}
          onClick={() => void chooseImport()}
        >
          Import
        </ButtonItem>
      </PanelSectionRow>
      {status && (
        <PanelSectionRow>
          <Field label={status.kind === 'success' ? 'Profile tools' : 'Error'}>
            <span
              style={{ color: status.kind === 'error' ? '#ff6b6b' : undefined }}
            >
              {status.message}
            </span>
          </Field>
        </PanelSectionRow>
      )}
    </>
  );
};

export default FanProfileTools;
