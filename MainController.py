import PySimpleGUI as sg
import mysql.connector


class VocException( Exception ):
    pass


class CampoException( Exception ):
    pass


class MainController:
    def __init__(self):
        self.__conexao = self.carregaConexao()
        self.__cursor = self.__conexao.cursor()

        # 1 - É a relação de tabelas com suas respectivas colunas
        # 2 - São os widgets a serem mostrados de acordo com o evento.
        # 3 - São os widgets a serem escondidos de acordo com o evento.
        self.__colunas_tabelas, self.__dicionario_mostra, self.__dicionario_esconde = {}, {}, {}
        # Mostra todos os possíveis tipos de registro, Nome, Tipo, Peso etc.
        self.__colunas, self.__lista_equipamentos, self.__atributos, self.__all_list_boxes = [], [], [], []
        # Tamanho da janela.
        self.__window_size = (500, 500)
        self.__window = sg.Window( 'Window', size=self.__window_size, layout=self.set_window_layout() )
        self.__window_tabela, self.__window_atributo = None, None
        self.__window_add_atributo, self.__window_del_atributo = None, None
        self.get_tabelas()
        self.carrega_dicionarios()  # Carrega os dicionário que mostram/escodem os elementos e a lista de colunas.

    def programa(self):
        while True:
            event, values = self.__window.read()
            if event in (sg.WIN_CLOSED, '_EXIT_'):
                break
            else:
                self.check_evento( event, values )
                self.check_telas( event, values )

    def check_evento(self, evento, valores):
        tabela_atual = ""
        if evento not in ('MouseWheel:Up', 'MouseWheel:Down', 'Cancel'):
            tabela_atual = valores['_equips_combo_'].lower()

        if evento == "_add_":
            if valores['_equips_combo_'] != 'Selecione':
                self.trata_dados_tabela( tabela_atual, valores )

        elif evento == "_add_del_atributo_":
            self.manage_atributos()

    def check_telas(self, botao, valores):
        try:
            tabela_atual = valores['_equips_combo_'].lower()
            if botao == '_equips_combo_':
                for i in self.__colunas:
                    self.__window[i].Update( visible=False )

                for i in self.__colunas_tabelas[tabela_atual]:
                    if "id" not in i:
                        i_text = '_text_' + i + '_'
                        self.__window[i_text].Update( visible=True )
                        self.__window[i].Update( visible=True )

            elif botao == '_voltar_equipamentos_':
                for i in self.__colunas:
                    self.__window[i].Update( visible=False )

            elif botao in self.__lista_equipamentos:
                pesquisa = self.pesquisar_banco( botao[1:-1], [], [], [], '*', '' )
                # self.__window["_list_equipamentos_"].Update( visible=True, values=pesquisa )
                colunas = self.__colunas_tabelas[botao[1:-1]]
                self.cria_tabela_exibicao( colunas, pesquisa, botao[1:-1] )

            if botao not in self.__lista_equipamentos:
                for i in self.__dicionario_mostra[botao]:
                    self.__window[i].Update( visible=True )

                for i in self.__dicionario_esconde[botao]:
                    self.__window[i].Update( visible=False )

        except KeyError:
            print( "Key Error", botao )
        except KeyboardInterrupt:
            pass

    def trata_dados_tabela(self, tabela_atual, valores):
        valores_tratados = []
        vocacoes = ['druid', 'knight', 'paladin', 'sorcerer']
        resultado = self.pesquisar_banco(
            'information_schema.columns', ['table_name', 'column_key'],
            [str( tabela_atual ), 'PRI'], ['=', '!='], 'column_name, data_type, is_nullable',
            'order by ordinal_position' )

        tamanho_lista = len( resultado )

        for col, type_column, is_nullable in resultado:
            check = valores[col].lower()
            try:
                if type_column == 'int':
                    check = int( valores[col] )
                elif type_column == 'float':
                    check = float( valores[col] )
                elif col == 'sVocacao':
                    if check not in vocacoes:
                        raise VocException
                if is_nullable == 'NO' and check == '':
                    raise CampoException

            except ValueError:
                if type_column == 'int':
                    sg.popup( title='Erro!', custom_text=f'Digite um valor inteiro para o campo {col[1:]}!' )
                elif type_column == 'float':
                    sg.popup( title='Erro!', custom_text=f'Digite um valor flutuante para o campo {col[1:]}!' )

                tamanho_lista -= 1
            except CampoException:
                sg.popup( title='Erro!', custom_text=f'O campo {col[1:]} é obrigatório!' )
                tamanho_lista -= 1
            except VocException:
                sg.popup( title='Erro!', custom_text=f'Digite uma vocação entre: {vocacoes}.' )
                tamanho_lista -= 1

            else:
                if check == '':
                    check = None
                valores_tratados.append( check )
            finally:
                if tamanho_lista != len( resultado ):
                    valores_tratados = []
        if valores_tratados:
            self.inserir_banco( tabela_atual, valores_tratados )
            sg.popup( title='Cadastro!', custom_text=f'Dados cadastrados com sucesso!' )

    def cria_tabela_exibicao(self, colunas, pesquisa, tabela):
        self.__all_list_boxes = []
        textos_colunas = []
        for i in range( len( colunas ) ):
            col = []
            textos_colunas.append( sg.Text( colunas[i].center( 10 ), key='_new_' + colunas[i] ) )
            for j in pesquisa:
                col.append( (j[i]) )

            self.__all_list_boxes.append(
                sg.Listbox( values=col, size=(10, 30), no_scrollbar=True,
                            pad=(0, 0), key="list_" + colunas[i] ) )

        self.__all_list_boxes = [self.__all_list_boxes]
        textos_colunas = [textos_colunas]
        self.__window_tabela = sg.Window( title=tabela.capitalize(), size=(len( colunas ) * 100, 350),
                                          layout=self.layout_colunas( textos_colunas ), use_ttk_buttons=True,
                                          finalize=True, resizable=True, modal=True )
        while True:
            event, values = self.__window_tabela.read()
            if event == "Cancel" or event == sg.WIN_CLOSED:
                break
        self.__window_tabela.close()

    def layout_colunas(self, textos_colunas):
        layout = [
            [sg.Frame( layout=[
                [sg.Column( textos_colunas, pad=(0, 0), key='_teste', justification='center' )],
                [sg.Column( self.__all_list_boxes, scrollable=True, pad=(0, 0), vertical_scroll_only=True,
                            justification='center', key='_coluna_valores_' )]], title='' )],
            [sg.Cancel( size=(20, 1) )]
        ]
        return layout

    def manage_atributos(self):
        self.__window_atributo = sg.Window( title='Atributos', size=(500, 350),
                                            layout=self.layout_atributos(), use_ttk_buttons=True,
                                            finalize=True, resizable=True, modal=True )
        # Inativa coluna do nome e deixa apenas o id selcionável.
        listbox1 = self.__window_atributo['_id_list_element_']
        listbox2 = self.__window_atributo['_name_list_element_']
        selecion = 0
        listbox1.Widget.configure( activestyle='none' )
        listbox2.Widget.configure( activestyle='none' )
        listbox1.Widget.select_set( 0 )

        while True:
            event, values = self.__window_atributo.read()
            tabela = values["_combo_element_equip"]
            self.carrega_lista_equips_em_atributos( event, values )

            try:
                if event == "_add_elemento_":
                    #if values["_id_list_element_"]:
                    id_equip = values["_id_list_element_"][0][0]
                    nome_equip = values["_name_list_element_"][0][0]

                    self.escolher_elemento( tabela, id_equip, nome_equip )
                elif event == "_del_elemento_":
                    id_equip = values["_id_list_element_"][0][0]
                    self.del_elemento( id_equip, values, tabela )
            except IndexError:
                sg.popup( title='Erro!', custom_text='Selecione um registro!' )
            if event in ['_id_list_element_', '_name_list_element_', 'Up:38', 'Down:40']:
                try:
                    selection = listbox1.get_indexes()[0]
                except IndexError:
                    pass
                else:
                    listbox1.update( set_to_index=selection )
                    listbox2.update( set_to_index=selection )
            if event == "Voltar" or event == sg.WIN_CLOSED:
                break

        self.__window_atributo.close()

    def carrega_lista_equips_em_atributos(self, event, values):
        try:
            chave = "_" + values[event].lower() + "_"
            if values["_combo_element_equip"] == "Aneis":
                chave_primaria = "idAnel"
            else:
                chave_primaria = "id" + values["_combo_element_equip"][0:-1]
            if chave in self.__lista_equipamentos:
                pesquisa_id = self.pesquisar_banco( values[event].lower(), [], [], [], chave_primaria, '' )
                pesquisa_nome = self.pesquisar_banco( values[event].lower(), [], [], [], "sNome", '' )
                self.__window_atributo["_id_list_element_"].Update( values=pesquisa_id )
                self.__window_atributo["_name_list_element_"].Update( values=pesquisa_nome )
        except KeyError:
            pass
        except AttributeError:
            pass
        except TypeError:
            pass
        except KeyboardInterrupt:
            pass

    def escolher_elemento(self, tabela, id_equip, nome_equip):
        layout = self.layout_add_atributos( id_equip, nome_equip )
        self.__window_add_atributo = sg.Window( title=nome_equip.capitalize(), size=(500, 350), layout=layout,
                                                use_ttk_buttons=True, finalize=True, resizable=True, modal=True )

        while True:
            event, values = self.__window_add_atributo.read()
            if event in (sg.WIN_CLOSED, '_voltar_'):
                break
            if event == "_add_elemento_":
                self.add_elemento( id_equip, values )
        self.__window_add_atributo.close()

    def add_elemento(self, id_equip, values):
        id_elemento, valor = -1, 0
        try:
            for id_elemento_layout in values:
                if id_elemento_layout > 14:
                    break
                elif values[id_elemento_layout]:
                    id_elemento = id_elemento_layout
                    break

            if id_elemento == -1:
                raise CampoException
            valor_porcentagem_inteiro = int( values[17] )
            if not str( valor_porcentagem_inteiro ):
                sg.popup( title='Erro!', custom_text='Digite um valor!' )
            if valor_porcentagem_inteiro <= 0 or valor_porcentagem_inteiro > 100:
                sg.popup( title='Erro!', custom_text='Digite um valor entre 0 e 100!' )

        except ValueError:
            sg.popup( title='Erro!', custom_text='Digite um valor inteiro!' )
        except TypeError:
            sg.popup( title='Erro!', custom_text='Digite um valor inteiro!' )
        except CampoException:
            sg.popup( title='Erro!', custom_text='Selecione um elemento.!' )
        except KeyboardInterrupt:
            pass
        else:
            # Inidica se será salvo no banco os sinais + ou -.
            if values[15]:
                string_ac_de = '+'
            else:
                string_ac_de = '-'
            self.inserir_banco( 'item_atributo',
                                [id_elemento, id_equip, valor_porcentagem_inteiro, string_ac_de] )

    def del_elemento(self, id_equip, values, tabela):
        dados = self.pesquisar_banco_join( ['Item_atributo', 'Atributos', tabela],
                                   ['sNome', 'sDescricao', 'nQuantidade', 'sTipo'],
                                   [tabela, 'atributos', 'item_atributo', 'item_atributo'],
                                   ['Nome', 'Atributo', 'Quantidade', 'Aumenta/Diminui'],
                                   [tabela], [self.colunas_tabelas[tabela.lower()][0]], [id_equip], ['='], '')
        dados_sem_id = []
        for i in dados:
            dados_sem_id.append(i[1:])
        layout = [
            [sg.Listbox( values=dados_sem_id, size=(30, 10), pad=(0, 0), key="_del_element_", no_scrollbar=True,
                         enable_events=True )],
            [sg.Button("Remover", key='_del_elemento_equip_')],
            [sg.Button("Cancelar", key='_cancelar_del_elemento_')]
        ]

        self.__window_del_atributo = sg.Window( title='Remover atributo', size=(500, 350), layout=layout,
                                                use_ttk_buttons=True, finalize=True, resizable=True, modal=True )
        while True:
            event, values = self.__window_del_atributo.read()

            if event in (sg.WIN_CLOSED, '_cancelar_del_elemento_'):
                break

            if event == "_del_elemento_equip_":
                try:
                    self.remover_banco("item_atributo", ['idAtributo', self.__colunas_tabelas[tabela.lower()][0]],
                                       [values["_del_element_"][0][0], id_equip])

                except KeyError:
                    sg.popup( title='Erro!', custom_text='Selecione um registro!' )

        self.__window_del_atributo.close()


    def pesquisar_banco_join(self, tabelas, colunas, tabelas_colunas, nome_apresentado,
                             tabela_condicao, condicoes, params_condicoes, sinais_condicoes, ordem):
        self.__conexao = self.carregaConexao()
        self.__cursor = self.__conexao.cursor()
        # Monta o script das colunas.
        if tabelas_colunas[0] != 'Aneis':
            coluna_consulta = 'id' + tabelas_colunas[0][0:-1] + ', '
        else:
            coluna_consulta = 'idAnel, '
        coluna_consulta += f'{tabelas[1]}.idAtributo, '
        for i in range(len(tabelas_colunas)):
            coluna_consulta += f'{tabelas_colunas[i]}.{colunas[i]} as "{nome_apresentado[i]}",\n'
        coluna_consulta = coluna_consulta[:-2]

        comando = f'select {coluna_consulta} from {tabelas[0]} {tabelas[0]} '
        # Insere os joins na consulta.
        for tabela in tabelas[2:]:
            if tabela != "Aneis":
                comando += f'\njoin {tabela} on {tabela}.{"id" + tabela[0:-1]} = {tabelas[0]}.idItem'
            else:
                comando += f'\njoin {tabela} on {tabela}.{"idAnel"} = {tabelas[0]}.idItem'

        comando += f'\njoin {tabelas[1]} on {tabelas[1]}.{"id" + tabelas[1][0:-1]} = {tabelas[0]}.idAtributo'

        # Insere as condições na consulta
        if condicoes:
            comando += " where "
            for i in range(len(condicoes)):
                comando += f'{tabela_condicao[i]}.{condicoes[i]} {sinais_condicoes[i]} {params_condicoes[i]} and '
            comando = comando[:-4]

        comando += ordem
        self.__cursor.execute( comando )
        resultado = self.__cursor.fetchall()
        # Fecha conexão.
        self.__cursor.close()
        self.__conexao.close()

        return resultado

    def layout_add_atributos(self, equip, nome_equip):
        # Criar opções elementos.
        radios, radios_ = [], []
        contador = 1
        for atributo in self.__atributos:
            radios.append( sg.Radio( atributo[1].capitalize(), group_id='elements' ) )
            if contador >= 3:
                radios_.append( radios )
                radios = []
                contador = 0
            elif atributo == self.__atributos[-1]:
                radios_.append( radios )
                break
            contador += 1

        layout = [
            [sg.Text( 'Escolha um elemento para o equipamento: ' + nome_equip.capitalize() )],
            # Cria opções dos elementos.
            radios_,
            # Cria opções de acréscimo ou decréscimo.
            [sg.Radio( "Acréscimo", group_id="tipo_alteracao", default=True ),
             sg.Radio( "Descréscimo", group_id="tipo_alteracao" )],
            # Campo para digitar a %.
            [sg.InputText( size=(5, 1) ), sg.Text( text='% da proteção' )],
            [sg.Button( button_text='Add Elemento', key='_add_elemento_', size=(20, 1) )],
            [sg.Button( button_text='Voltar', key='_voltar_', size=(20, 1) )]]
        return layout

    def layout_atributos(self):
        layout = [
            [sg.Combo( ['Acessorios', 'Amuletos', 'Aneis', 'Armas', 'Armaduras',
                        'Botas', 'Calcas', 'Elmos', 'Escudos', 'Livros'],
                       key='_combo_element_equip', default_value='Selecione', readonly=True, enable_events=True )],
            [sg.Listbox( values=[], size=(5, 10), pad=(0, 0), key="_id_list_element_", no_scrollbar=True,
                         enable_events=True ),
             sg.Listbox( values=[], size=(20, 10), pad=(0, 0), key="_name_list_element_", enable_events=True )],
            [sg.Button( button_text='Add Elemento', key='_add_elemento_', size=(20, 1) )],
            [sg.Button( button_text='Del Elemento', key='_del_elemento_', size=(20, 1) )],
            [sg.Cancel( button_text='Voltar', size=(20, 1) )]
        ]
        return layout

    def set_window_layout(self):
        sg.theme( 'DarkAmber' )
        tamanho_botao = (20, 1)

        layout = [
            [sg.pin( sg.Text( '\n\nEscolha o melhor set para sua hunt.', key='_texto_menu_' ) )],
            [sg.Text()],
            [sg.Button( 'Elemento', size=tamanho_botao, key='_elemento_' )],
            [sg.Button( 'Equipamentos', size=tamanho_botao, key='_equipamentos_' )],
            [sg.Button( 'Inserir/Remover', size=tamanho_botao, key='_inserir_' )],
            [sg.Button( 'Inserir/Remover Atributo', size=tamanho_botao, key='_add_del_atributo_' )],

            [sg.pin( sg.Text( '\n\nEscolha um elemento.', key='_texto_elemento_', visible=False ) )],
            [sg.Checkbox( 'Fogo', key='_fogo_', visible=False ),
             sg.Checkbox( 'Gelo', key='_gelo_', visible=False ),
             sg.Checkbox( 'Terra', key='_terra_', visible=False ),
             sg.Checkbox( 'Energia', key='_energia_', visible=False )],

            [sg.Checkbox( 'Sagrado', key='_sagrado_', visible=False ),
             sg.Checkbox( 'Morte', key='_morte_', visible=False ),
             sg.Checkbox( 'Físico', key='_fisico_', visible=False )],

            [sg.Text( 'Equipamentos', key='_text_equipamentos_', visible=False )],
            [sg.pin( sg.Button( 'Acessorios', key='_acessorios_', size=tamanho_botao, visible=False ) ),
             sg.Button( 'Amuletos', key='_amuletos_', size=tamanho_botao, visible=False )],
            [sg.pin( sg.Button( 'Aneis', key='_aneis_', size=tamanho_botao, visible=False ) ),
             sg.Button( 'Armas', key='_armas_', size=tamanho_botao, visible=False )],
            [sg.pin( sg.Button( 'Armaduras', key='_armaduras_', size=tamanho_botao, visible=False ) ),
             sg.Button( 'Botas', key='_botas_', size=tamanho_botao, visible=False )],
            [sg.pin( sg.Button( 'Calcas', key='_calcas_', size=tamanho_botao, visible=False ) ),
             sg.Button( 'Elmos', key='_elmos_', size=tamanho_botao, visible=False )],
            [sg.pin( sg.Button( 'Escudos', key='_escudos_', size=tamanho_botao, visible=False ) ),
             sg.Button( 'Livros', key='_livros_', size=tamanho_botao, visible=False )],

            [sg.Combo( ['Acessorios', 'Amuletos', 'Aneis', 'Armas', 'Armaduras',
                        'Botas', 'Calcas', 'Elmos', 'Escudos', 'Livros'],
                       key='_equips_combo_', default_value='Selecione', readonly=True, visible=False,
                       enable_events=True )],

            self.add_registro_secao(),

            [sg.Button( 'Adicionar', key='_add_', visible=False ), sg.Button( 'Remover', key='_del_', visible=False )],

            [sg.Column( self.__all_list_boxes, scrollable=True, pad=(0, 0), expand_y=True, expand_x=True,
                        key='_coluna_valores_', visible=False )],
            [sg.Button( "Voltar", key="_voltar_equipamentos_", size=tamanho_botao, visible=False )],

            [sg.pin( sg.Button( 'Confirmar', key='_confirmar_elemento_', size=(20, 1), visible=False ) )],
            [sg.pin( sg.Button( "Voltar", key="_voltar_elemento_", size=(20, 1), visible=False ) )],
            [sg.Cancel( 'Sair', size=(20, 1), key='_EXIT_' )]
        ]
        return layout

    def add_registro_secao(self):
        tamanho_campos = (10, 1)
        teste = [[sg.pin( sg.Text( 'Peso', size=tamanho_campos, key='_text_fPeso_', visible=False ) ),
                  sg.InputText( key='fPeso', visible=False )],
                 [sg.pin( sg.Text( 'Arm', size=tamanho_campos, key='_text_nArm_', visible=False ) ),
                  sg.InputText( key='nArm', visible=False )],
                 [sg.pin( sg.Text( 'Atk', size=tamanho_campos, key='_text_nAtk_', visible=False ) ),
                  sg.InputText( key='nAtk', visible=False )],
                 [sg.pin( sg.Text( 'Cargas', size=tamanho_campos, key='_text_nCargas_', visible=False ) ),
                  sg.InputText( key='nCargas', visible=False )],
                 [sg.pin( sg.Text( 'Duração', size=tamanho_campos, key='_text_nDuracao_', visible=False ) ),
                  sg.InputText( key='nDuracao', visible=False )],
                 [sg.pin( sg.Text( 'Def', size=tamanho_campos, key='_text_nDef_', visible=False ) ),
                  sg.InputText( key='nDef', visible=False )],
                 [[sg.pin( sg.Text( 'Duas Mãos', size=tamanho_campos, key='_text_nDuasMaos_', visible=False ) ),
                   sg.Checkbox( text='Sim', key='nDuasMaos', visible=False ),
                   sg.Checkbox( text='Nao', key='nDuasMaos', visible=False )]],
                 [sg.pin( sg.Text( 'Nível Mínimo', size=tamanho_campos, key='_text_nNivelMinimo_', visible=False ) ),
                  sg.InputText( key='nNivelMinimo', visible=False )],
                 [sg.pin( sg.Text( 'Imbuiments', size=tamanho_campos, key='_text_nQtImbuiSlot_', visible=False ) ),
                  sg.InputText( key='nQtImbuiSlot', visible=False )],
                 [sg.pin( sg.Text( 'Nome', size=tamanho_campos, key='_text_sNome_', visible=False ) ),
                  sg.InputText( key='sNome', visible=False )],
                 [sg.pin( sg.Text( 'Tipo', size=tamanho_campos, key='_text_sTipo_', visible=False ) ),
                  sg.InputText( key='sTipo', visible=False )],
                 [sg.pin( sg.Text( 'Vocação', size=tamanho_campos, key='_text_sVocacao_', visible=False ) ),
                  sg.InputText( key='sVocacao', visible=False )]]
        return teste

    def pesquisar_banco(self, tabela, condicoes, params_condicoes, sinais_condicoes, colunas, ordem):
        # Abre conexão.
        self.__conexao = self.carregaConexao()
        self.__cursor = self.__conexao.cursor()
        # Comando utilizando para consulta no banco.
        comando = f'select {colunas} from {tabela}'
        if condicoes:
            comando += ' where '
            for i in range( len( condicoes ) ):
                comando += condicoes[i]
                comando += ' '
                comando += sinais_condicoes[i]
                comando += " '"
                comando += params_condicoes[i]
                comando += "'"

                if i < len( condicoes ) - 1:
                    comando += ' and '

        comando += ordem
        self.__cursor.execute( comando )
        resultado = self.__cursor.fetchall()
        # Fecha conexão.
        self.__cursor.close()
        self.__conexao.close()
        return resultado

    def inserir_banco(self, tabela, valores_tratados):
        self.__conexao = self.carregaConexao()
        self.__cursor = self.__conexao.cursor()
        # Separa as colunas de forma que atenda a syntax do banco.
        tabela_parametros = "("
        for i in self.__colunas_tabelas[tabela]:
            if "id" not in i or tabela == 'item_atributo':
                tabela_parametros += i
                tabela_parametros += ", "
        tabela_parametros = tabela_parametros[:-2]
        tabela_parametros += ")"
        try:
            comando = f'insert into {tabela} {tabela_parametros} values {tuple( valores_tratados )}'
            if None in valores_tratados:
                print( comando )
            self.__cursor.execute( comando )
        except mysql.connector.errors.DataError:
            print( "Insira os dados conforme as colunas: ", tabela_parametros + "." )
        else:
            print( "inseriu dados" )
            self.__conexao.commit()
            sg.popup( title='Cadastro', custom_text='Dado cadastrado com sucesso!' )

        self.__cursor.close()
        self.__conexao.close()

    def remover_banco(self, tabela, coluna_condicao, dados):
        self.__conexao = self.carregaConexao()
        self.__cursor = self.__conexao.cursor()

        comando = f'delete from {tabela} where '

        for i in range(len(coluna_condicao)):
            comando += f'{coluna_condicao[i]} = {dados[i]} and '

        comando = comando[:-4]
        print( "comando",comando )
        try:
            self.__cursor.execute( comando )
        except Exception as e:
            print(e)
        else:
            print(comando)
            self.__conexao.commit()
            sg.popup( title='Remover Atributo', custom_text='Atributo removido com sucesso!' )

        self.__cursor.close()
        self.__conexao.close()

    def get_colunas_tabela(self, tabela):
        comando = f'select column_name from information_schema.columns where table_name = "{tabela}" ' \
                  f'order by ordinal_position'

        self.__cursor.execute( comando )
        resultado = self.__cursor.fetchall()

        for coluna in resultado:
            self.__colunas_tabelas[tabela] += coluna

    def get_tabelas(self):
        comando_sql = 'show tables'
        self.__cursor.execute( comando_sql )
        resultado = self.__cursor.fetchall()
        for tabela_un in resultado:
            self.__colunas_tabelas[tabela_un[0]] = []
            self.get_colunas_tabela( tabela_un[0] )
        self.__cursor.close()
        self.__conexao.close()

    def carregaConexao(self):
        return mysql.connector.connect(
            user='root',
            password='feef',
            host='localhost',
            database='equipamentos'
        )

    def carrega_dicionarios(self):
        self.__dicionario_mostra = {
            "_elemento_": ["_fogo_", "_energia_", "_gelo_", "_terra_", "_fisico_", "_morte_", "_sagrado_",
                           "_confirmar_elemento_", "_voltar_elemento_", "_texto_menu_"],
            "_voltar_elemento_": ["_elemento_", "_EXIT_", "_texto_menu_", "_equipamentos_", "_inserir_",
                                  "_add_del_atributo_"],
            "_confirmar_elemento_": [],
            "_equipamentos_": ["_acessorios_", "_amuletos_", "_armaduras_", "_aneis_", "_armas_", "_botas_", "_calcas_",
                               "_escudos_", "_elmos_", "_livros_", "_text_equipamentos_", "_voltar_equipamentos_"],
            "_voltar_equipamentos_": ["_texto_menu_", "_elemento_", "_EXIT_", "_equipamentos_", "_inserir_",
                                      "_add_del_atributo_"],
            "_inserir_": ["_equips_combo_", "_add_", "_del_", "_voltar_equipamentos_"],
            "_add_": [],
            "_del_": [],
            "_equips_combo_": [],
            "_equip_": ["_coluna_valores_"]
        }
        self.__dicionario_esconde = {
            "_elemento_": ["_texto_menu_", "_elemento_", "_EXIT_", "_equipamentos_", "_inserir_", "_add_del_atributo_"],
            "_voltar_elemento_": ["_fogo_", "_energia_", "_gelo_", "_terra_",
                                  "_fisico_", "_morte_", "_sagrado_",
                                  "_confirmar_elemento_", "_voltar_elemento_", "_texto_elemento_"],
            "_confirmar_elemento_": [],
            "_equipamentos_": ["_texto_menu_", "_elemento_", "_EXIT_", "_equipamentos_", "_inserir_", "_inserir_",
                               "_add_del_atributo_"],
            "_voltar_equipamentos_": ["_acessorios_", "_amuletos_", "_armaduras_", "_aneis_", "_armas_", "_botas_",
                                      "_calcas_", "_escudos_", "_elmos_", "_livros_",
                                      "_text_equipamentos_", "_voltar_equipamentos_",
                                      "_equips_combo_", "_add_", "_del_"],
            "_inserir_": ["_texto_menu_", "_elemento_", "_EXIT_", "_equipamentos_", "_inserir_", "_add_del_atributo_"],
            "_add_": [],
            "_del_": [],
            "_equips_combo_": [],
            "_equip_": ["_elemento_", "_equipamentos_", "_inserir_", "_equips_combo_"]
        }

        self.__colunas = [
            'fPeso', 'nArm', 'nAtk', 'nCargas', 'nDuracao', 'nDef', 'nDuasMaos', 'nNivelMinimo', 'nQtImbuiSlot',
            'sNome', 'sTipo', 'sVocacao',
            '_text_fPeso_', '_text_nArm_', '_text_nAtk_', '_text_nCargas_', '_text_nDuracao_', '_text_nDef_',
            '_text_nDuasMaos_', '_text_nNivelMinimo_', '_text_nQtImbuiSlot_', '_text_sNome_', '_text_sTipo_',
            '_text_sVocacao_'
        ]

        self.__lista_equipamentos = ['_acessorios_', '_amuletos_', '_aneis_', '_armas_',
                                     '_armaduras_', '_botas_', '_calcas_', '_elmos_', '_escudos_', '_livros_']

        self.__atributos = self.pesquisar_banco( 'atributos', [], [], [], '*', '' )

    @property
    def colunas_tabelas(self):
        return self.__colunas_tabelas

    @colunas_tabelas.setter
    def colunas_tabelas(self, colunas_tabelas):
        self.__colunas_tabelas = colunas_tabelas
